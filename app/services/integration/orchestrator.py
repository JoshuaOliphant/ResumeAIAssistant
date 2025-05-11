"""
Task Orchestrator Implementation for ResumeAIAssistant.

This module implements the Task Orchestrator interface to provide a unified
integration layer for the parallel processing architecture.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Set
import logfire

from app.services.integration.interfaces import (
    Task, TaskOrchestrator, Priority, TaskStatus, TaskResult, ProgressTracker
)
from app.services.parallel_processor import (
    ParallelProcessor, ParallelTaskScheduler, ParallelTask as PPTask, TaskPriority
)


class OrchestratorTask(Task):
    """Implementation of the Task interface using the parallel processor architecture."""
    
    def __init__(self, name: str, priority: Priority = Priority.MEDIUM, **kwargs):
        """
        Initialize an orchestrator task.
        
        Args:
            name: Name of the task
            priority: Priority level
            **kwargs: Additional task parameters
        """
        super().__init__(name, priority)
        self.kwargs = kwargs
        self._pp_task: Optional[PPTask] = None
        
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """
        Execute the task and return result.
        
        Args:
            context: Execution context
            
        Returns:
            Task execution result
        """
        try:
            if hasattr(self, '_execute_impl'):
                result = await self._execute_impl(context)
                return TaskResult(success=True, data=result)
            else:
                return TaskResult(
                    success=False, 
                    error="Task doesn't implement _execute_impl method"
                )
        except Exception as e:
            logfire.error(f"Task execution failed: {str(e)}", task_name=self.name)
            return TaskResult(success=False, error=str(e))


class IntegratedTaskOrchestrator(TaskOrchestrator):
    """Implementation of the TaskOrchestrator interface using the parallel processor."""
    
    def __init__(self, max_concurrent_tasks: int = 5):
        """
        Initialize the task orchestrator.
        
        Args:
            max_concurrent_tasks: Maximum number of tasks to run concurrently
        """
        self.tasks: Dict[str, Task] = {}
        self.results: Dict[str, TaskResult] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.parallel_processor = ParallelProcessor()
        self.scheduler = ParallelTaskScheduler(max_concurrent_tasks=max_concurrent_tasks)
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.progress_tracker: Optional[ProgressTracker] = None
        
    async def add_task(self, task: Task, dependencies: Optional[List[str]] = None) -> None:
        """
        Add a task to the orchestrator with optional dependencies.
        
        Args:
            task: The task to add
            dependencies: Optional list of task names that this task depends on
        """
        self.tasks[task.id] = task
        
        # Set up dependencies
        if dependencies:
            task.dependencies = dependencies.copy()
            
        # Log task addition
        logfire.info(
            "Added task to orchestrator",
            task_id=task.id,
            task_name=task.name,
            priority=task.priority,
            dependencies=task.dependencies
        )
    
    async def execute_all(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, TaskResult]:
        """
        Execute all tasks respecting dependencies and return results.
        
        Args:
            context: Optional execution context
            
        Returns:
            Dictionary mapping task IDs to results
        """
        context = context or {}
        start_time = time.time()
        
        # Update progress tracking if available
        if self.progress_tracker:
            await self.progress_tracker.initialize(
                task_count=len(self.tasks),
                operation_id=str(uuid.uuid4())
            )
        
        # Create dependency graph
        dependency_graph = self._create_dependency_graph()
        
        # Convert tasks to ParallelProcessor tasks
        pp_tasks = {}
        for task_id, task in self.tasks.items():
            priority = TaskPriority.MEDIUM
            
            # Map priority
            if task.priority == Priority.CRITICAL:
                priority = TaskPriority.CRITICAL
            elif task.priority == Priority.HIGH:
                priority = TaskPriority.HIGH
            elif task.priority == Priority.MEDIUM:
                priority = TaskPriority.MEDIUM
            elif task.priority == Priority.LOW:
                priority = TaskPriority.LOW
                
            # Create parallel processor task
            pp_task = PPTask(
                id=task_id,
                name=task.name,
                priority=priority,
                func=self._execute_task,
                args=[task, context],
                depends_on=task.dependencies
            )
            
            # Add to scheduler
            self.scheduler.add_task(pp_task)
            pp_tasks[task_id] = pp_task
            
        # Execute all tasks
        pp_results = await self.scheduler.execute_all()
        
        # Collect results
        for task_id, result in pp_results.items():
            self.results[task_id] = result
            
        # Mark tasks as completed or failed
        for task_id, task in self.tasks.items():
            if task_id in self.scheduler.completed_tasks:
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.add(task_id)
            elif task_id in self.scheduler.failed_tasks:
                task.status = TaskStatus.FAILED
                self.failed_tasks.add(task_id)
        
        duration = time.time() - start_time
        logfire.info(
            "Task orchestrator execution completed",
            completed_count=len(self.completed_tasks),
            failed_count=len(self.failed_tasks),
            total_duration_seconds=round(duration, 2)
        )
        
        return self.results
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task if possible.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.PENDING:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            
            # Try to cancel in the scheduler if present
            if hasattr(self.scheduler, 'cancel_task'):
                self.scheduler.cancel_task(task_id)
                
            logfire.info("Task cancelled", task_id=task_id)
            return True
            
        return False
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Current task status or None if task not found
        """
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    async def _execute_task(self, task: Task, context: Dict[str, Any]) -> Any:
        """
        Execute a single task with progress tracking.
        
        Args:
            task: The task to execute
            context: Execution context
            
        Returns:
            Task result
        """
        # Update progress if tracker available
        if self.progress_tracker:
            await self.progress_tracker.update_progress(
                task_id=task.id,
                percent_complete=0.0,
                status="started",
                message=f"Starting task {task.name}"
            )
        
        start_time = time.time()
        task.status = TaskStatus.RUNNING
        self.running_tasks.add(task.id)
        
        try:
            # Execute the task
            result = await task.execute(context)
            
            # Update task status and record result
            task.status = TaskStatus.COMPLETED
            task.result = result
            self.completed_tasks.add(task.id)
            self.running_tasks.discard(task.id)
            
            # Update progress
            if self.progress_tracker:
                await self.progress_tracker.complete_task(
                    task_id=task.id,
                    success=True,
                    message=f"Task {task.name} completed successfully"
                )
            
            duration = time.time() - start_time
            logfire.info(
                "Task completed successfully",
                task_id=task.id,
                task_name=task.name,
                duration_seconds=round(duration, 2)
            )
            
            return result
            
        except Exception as e:
            # Update task status and record error
            task.status = TaskStatus.FAILED
            self.failed_tasks.add(task.id)
            self.running_tasks.discard(task.id)
            
            # Create error result
            error_result = TaskResult(success=False, error=str(e))
            task.result = error_result
            
            # Update progress
            if self.progress_tracker:
                await self.progress_tracker.complete_task(
                    task_id=task.id,
                    success=False,
                    message=f"Task {task.name} failed: {str(e)}"
                )
            
            duration = time.time() - start_time
            logfire.error(
                "Task execution failed",
                task_id=task.id,
                task_name=task.name,
                error=str(e),
                duration_seconds=round(duration, 2)
            )
            
            return error_result
    
    def _create_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Create a dependency graph for tasks.
        
        Returns:
            Dictionary mapping task IDs to lists of dependent task IDs
        """
        graph = {task_id: [] for task_id in self.tasks}
        
        # Build forward dependency graph
        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id in graph:
                    graph[dep_id].append(task_id)
        
        return graph