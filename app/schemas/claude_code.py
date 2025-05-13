"""
Pydantic schemas for Claude Code API.

This module provides schemas for the Claude Code customization API,
including task tracking and result schemas.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class QueuedTaskResponse(BaseModel):
    """
    Response model for a queued customization task.
    
    Attributes:
        task_id: Unique identifier for the task
        status: Current status of the task (e.g., "queued", "processing")
    """
    task_id: str = Field(..., description="Unique identifier for tracking the task")
    status: str = Field(..., description="Current status of the task")


class TaskStatusResponse(BaseModel):
    """
    Response model for task status requests.
    
    Attributes:
        task_id: Unique identifier for the task
        status: Current status of the task
        progress: Progress percentage (0-100)
        message: Human-readable status message
        result: Optional task result data (only present when status is "completed")
        error: Optional error message (only present when status is "error")
    """
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(
        ..., 
        description="Current status (initializing, analyzing, planning, implementing, completed, error)"
    )
    progress: int = Field(
        ..., 
        description="Progress percentage (0-100)", 
        ge=0, 
        le=100
    )
    message: str = Field(..., description="Human-readable status message")
    result: Optional[Dict[str, Any]] = Field(
        None, 
        description="Task result data (only present when status is 'completed')"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message (only present when status is 'error')"
    )
    created_at: Optional[float] = Field(
        None, 
        description="Unix timestamp when the task was created"
    )
    updated_at: Optional[float] = Field(
        None, 
        description="Unix timestamp when the task was last updated"
    )


class ClaudeCodeError(BaseModel):
    """
    Error response model for Claude Code API.
    
    Attributes:
        error: Error message
        error_type: Type of error
        status_code: HTTP status code
    """
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    status_code: int = Field(..., description="HTTP status code")