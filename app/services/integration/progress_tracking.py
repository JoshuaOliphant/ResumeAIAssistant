"""
Progress Tracking Implementation for ResumeAIAssistant.

This module implements the ProgressTracker interface to provide a unified
integration layer for progress tracking and reporting.
"""

import asyncio
import time
import httpx
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import logfire
from pydantic import BaseModel, Field

from app.services.integration.interfaces import ProgressTracker
from app.core.config import settings


class ProgressStageModel(BaseModel):
    """Represents a stage in a multi-stage process with its own progress tracking."""
    
    name: str
    description: str
    progress: float = Field(0.0, ge=0.0, le=1.0)
    status: str = "pending"  # pending, in_progress, completed, error
    message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None  # in seconds


class ProgressUpdate(BaseModel):
    """Progress update model that will be sent through WebSockets."""
    
    task_id: str
    overall_progress: float = Field(0.0, ge=0.0, le=1.0)
    status: str = "in_progress"  # initialization, in_progress, completed, error
    current_stage: Optional[str] = None
    stages: Dict[str, ProgressStageModel] = {}
    message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None  # in seconds
    started_at: Optional[str] = None
    updated_at: Optional[str] = None


class IntegratedProgressTracker(ProgressTracker):
    """Implementation of the ProgressTracker interface for integrated progress reporting."""
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.task_id = None
        self.operation_id = None
        self.task_count = 0
        self.completed_tasks = 0
        self.started_at = None
        self.last_updated_at = None
        self.overall_progress = 0.0
        self.status = "initializing"
        self.message = "Initializing task"
        self.stages = {}
        self.api_url = f"{settings.API_URL}/progress/update" if hasattr(settings, 'API_URL') else None
        self.current_stage = None
        
    async def initialize(self, task_count: int, operation_id: str) -> None:
        """
        Initialize tracker with expected task count.
        
        Args:
            task_count: Number of tasks to track
            operation_id: Unique ID for this operation
        """
        self.task_id = operation_id
        self.operation_id = operation_id
        self.task_count = task_count
        self.completed_tasks = 0
        self.started_at = datetime.now().isoformat()
        self.last_updated_at = self.started_at
        self.overall_progress = 0.0
        self.status = "initializing"
        self.message = f"Initializing task with {task_count} operations"
        
        # Initialize default stages
        self.stages = {
            "initialization": ProgressStageModel(
                name="initialization",
                description="Setting up resources and preparing for processing",
                progress=0.0,
                status="pending"
            ),
            "processing": ProgressStageModel(
                name="processing",
                description="Processing tasks",
                progress=0.0,
                status="pending"
            ),
            "finalization": ProgressStageModel(
                name="finalization",
                description="Finalizing and assembling results",
                progress=0.0,
                status="pending"
            )
        }
        
        self.current_stage = "initialization"
        self.stages["initialization"].status = "in_progress"
        
        # Send initial update
        await self._send_update()
        
        logfire.info(
            "Progress tracker initialized",
            task_id=self.task_id,
            task_count=self.task_count
        )
        
    async def update_progress(self, task_id: str, percent_complete: float, 
                            status: str = None, message: str = None) -> None:
        """
        Update progress for a specific task.
        
        Args:
            task_id: ID of the task to update
            percent_complete: Progress percentage (0-100)
            status: Optional status message
            message: Optional progress message
        """
        if not self.task_id:
            return
            
        # If we're still in initialization and progress > 0, switch to processing
        if self.current_stage == "initialization" and percent_complete > 0:
            await self.complete_stage("initialization")
            self.current_stage = "processing"
            self.stages["processing"].status = "in_progress"
        
        # For processing stage, update based on individual task progress
        if self.current_stage == "processing":
            # Task-specific progress info can be stored if needed
            pass
        
        # Compute overall progress based on completed tasks and current task progress
        if self.task_count > 0:
            # Contributed progress from completed tasks
            completed_progress = (self.completed_tasks / self.task_count)
            
            # Contributed progress from current task (weighted by 1/task_count)
            current_task_progress = (percent_complete / 100.0) / self.task_count
            
            # Overall is sum of completed tasks progress and current task contribution
            self.overall_progress = min(0.99, completed_progress + current_task_progress)
        
        # Update message if provided
        if message:
            self.message = message
        elif status:
            self.message = f"Processing: {status}"
        
        # Update stage progress
        self.stages[self.current_stage].progress = self.overall_progress
        if message:
            self.stages[self.current_stage].message = message
        
        # Send update
        await self._send_update()
        
    async def complete_task(self, task_id: str, success: bool = True, 
                          message: str = None) -> None:
        """
        Mark a task as complete.
        
        Args:
            task_id: ID of the task to mark as complete
            success: Whether the task completed successfully
            message: Optional completion message
        """
        if not self.task_id:
            return
            
        # Increment completed tasks count
        self.completed_tasks += 1
        
        # If all tasks completed, move to finalization stage
        if self.completed_tasks >= self.task_count:
            if self.current_stage != "finalization":
                await self.complete_stage(self.current_stage)
                self.current_stage = "finalization"
                self.stages["finalization"].status = "in_progress"
                self.stages["finalization"].progress = 0.5
        
        # Compute overall progress
        if self.task_count > 0:
            self.overall_progress = min(0.99, self.completed_tasks / self.task_count)
        
        # Update message if provided
        if message:
            self.message = message
        else:
            self.message = f"Completed {self.completed_tasks} of {self.task_count} tasks"
        
        # Update stage progress
        self.stages[self.current_stage].progress = self.overall_progress
        if message:
            self.stages[self.current_stage].message = message
        
        # If all tasks completed and we're in finalization, complete the operation
        if self.completed_tasks >= self.task_count and self.current_stage == "finalization":
            self.stages["finalization"].progress = 1.0
            self.stages["finalization"].status = "completed"
            self.overall_progress = 1.0
            self.status = "completed"
            self.message = "Operation completed successfully"
        
        # Send update
        await self._send_update()
        
    async def get_overall_progress(self) -> Dict[str, Any]:
        """
        Get the overall progress of all tasks.
        
        Returns:
            Dictionary with progress details
        """
        return {
            "task_id": self.task_id,
            "task_count": self.task_count,
            "completed_tasks": self.completed_tasks,
            "overall_progress": self.overall_progress,
            "status": self.status,
            "message": self.message,
            "current_stage": self.current_stage,
            "stages": {name: stage.dict() for name, stage in self.stages.items()},
            "started_at": self.started_at,
            "updated_at": self.last_updated_at
        }
        
    async def complete_stage(self, stage_name: str, message: str = None) -> None:
        """
        Mark a stage as completed.
        
        Args:
            stage_name: Name of the stage to complete
            message: Optional completion message
        """
        if stage_name not in self.stages:
            return
            
        # Mark stage as completed
        self.stages[stage_name].status = "completed"
        self.stages[stage_name].progress = 1.0
        
        # Update message if provided
        if message:
            self.stages[stage_name].message = message
        else:
            self.stages[stage_name].message = f"Completed {stage_name} stage"
        
        # Send update
        await self._send_update()
        
    async def _send_update(self) -> None:
        """Send progress update to the API endpoint."""
        if not self.api_url:
            return
            
        self.last_updated_at = datetime.now().isoformat()
        
        update = ProgressUpdate(
            task_id=self.task_id,
            overall_progress=self.overall_progress,
            status=self.status,
            current_stage=self.current_stage,
            stages={name: stage for name, stage in self.stages.items()},
            message=self.message,
            estimated_time_remaining=None,  # Could calculate based on progress rate
            started_at=self.started_at,
            updated_at=self.last_updated_at
        )
        
        # Send the update to the API using httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=update.dict(),
                    timeout=5.0
                )
                
                if response.status_code != 200:
                    logfire.warning(
                        "Failed to send progress update",
                        status_code=response.status_code,
                        response=response.text
                    )
        except Exception as e:
            # Don't fail the main task if progress updates fail
            logfire.warning(
                "Error sending progress update",
                error=str(e),
                task_id=self.task_id
            )