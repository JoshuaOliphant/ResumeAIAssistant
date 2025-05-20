"""
Progress Tracking System for Claude Code Resume Customization

This module implements a task tracking system for long-running
Claude Code customization tasks, providing real-time progress
updates to clients.
"""

import time
import uuid
import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable, Set

logger = logging.getLogger(__name__)

class Task:
    """
    Represents a running customization task with progress tracking.
    """
    def __init__(self, task_id: str):
        """
        Initialize a tracked task.
        
        Args:
            task_id: Unique identifier for the task
        """
        self._task_id = task_id
        self.status = "initializing"
        self.progress = 0
        self.message = "Task initialized"
        self.created_at = time.time()
        self.updated_at = time.time()
        self.result = None
        self.error = None
        self.subscribers: Set[asyncio.Queue] = set()
        self.context = {}  # For storing task-specific context data
        
    @property
    def task_id(self) -> str:
        """Get the task ID"""
        return self._task_id
        
    @task_id.setter
    def task_id(self, value: str):
        """
        Set the task ID and ensure it's properly registered in the tracker.
        This is used when a client provides a custom task ID.
        """
        # Skip if value is the same
        if value == self._task_id:
            return
            
        old_id = self._task_id
        self._task_id = value
        
        # Get tracker singleton to update the task registry
        # This is not ideal from a design perspective, but safer than letting tasks become orphaned
        tracker = progress_tracker
        
        # Update the tasks dictionary to use the new ID
        with tracker.lock:
            # Remove the old entry if it exists
            if old_id in tracker.tasks and tracker.tasks[old_id] == self:
                del tracker.tasks[old_id]
                
            # Add with new ID
            tracker.tasks[value] = self
            logger.info(f"Task ID updated from {old_id} to {value}, total tasks: {len(tracker.tasks)}")
        
    def update(self, status: str, progress: int, message: str):
        """
        Update the task status and notify subscribers.
        
        Args:
            status: Current status of the task
            progress: Progress percentage (0-100)
            message: Human-readable status message
        """
        self.status = status
        self.progress = progress
        self.message = message
        self.updated_at = time.time()
        
        # Notify all subscribers of the update
        for queue in list(self.subscribers):
            try:
                if not queue.full():
                    queue.put_nowait(self.to_dict())
            except Exception as e:
                logger.error(f"Error notifying subscriber for task {self.task_id}: {str(e)}")
    
    def add_subscriber(self, queue: asyncio.Queue):
        """
        Add a subscriber to receive progress updates.
        
        Args:
            queue: AsyncIO queue to receive updates
        """
        self.subscribers.add(queue)
        
    def remove_subscriber(self, queue: asyncio.Queue):
        """
        Remove a subscriber from updates.
        
        Args:
            queue: AsyncIO queue to remove
        """
        if queue in self.subscribers:
            self.subscribers.remove(queue)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary representation.
        
        Returns:
            Dictionary containing task status information
        """
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error
        }
    
    def set_result(self, result: Dict[str, Any]):
        """
        Set the final result of the task.
        
        Args:
            result: Task result data
        """
        self.result = result
        self.update("completed", 100, "Task completed successfully")
    
    def set_error(self, error: str):
        """
        Set an error status for the task.
        
        Args:
            error: Error message
        """
        self.error = error
        self.update("error", 0, f"Error: {error}")


class ProgressTracker:
    """
    Singleton task tracking service that manages task progress
    and handles subscriptions to progress updates.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProgressTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize task tracker state."""
        self.tasks: Dict[str, Task] = {}
        self.lock = threading.RLock()
        self.cleanup_interval = 3600  # 1 hour
        self.max_task_age = 24 * 3600  # 24 hours
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_tasks)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
    
    def create_task(self) -> Task:
        """
        Create a new tracked task.
        
        Returns:
            New task object
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id)
        
        with self.lock:
            # Store task in tasks dictionary with the auto-generated ID
            self.tasks[task_id] = task
            logger.info(f"Created new task with ID {task_id}, total tasks: {len(self.tasks)}")
            
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            Task if found, None otherwise
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def update_task(
        self, 
        task_id: str, 
        status: str, 
        progress: int, 
        message: str
    ) -> bool:
        """
        Update a task's progress and status.
        
        Args:
            task_id: Task to update
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            
        Returns:
            True if task was found and updated, False otherwise
        """
        task = self.get_task(task_id)
        if task:
            task.update(status, progress, message)
            return True
        return False
    
    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all tasks, optionally filtered by status.
        
        Args:
            status: Filter to show only tasks with this status
            
        Returns:
            List of task dictionaries
        """
        with self.lock:
            task_list = list(self.tasks.values())
            
        if status:
            task_list = [task for task in task_list if task.status == status]
            
        return [task.to_dict() for task in task_list]
    
    def _cleanup_old_tasks(self):
        """
        Periodically remove old completed or failed tasks.
        """
        while True:
            try:
                now = time.time()
                to_remove = []
                
                with self.lock:
                    for task_id, task in self.tasks.items():
                        # Remove completed or errored tasks older than max_task_age
                        if (task.status in ["completed", "error"] and 
                            now - task.updated_at > self.max_task_age):
                            to_remove.append(task_id)
                    
                    # Remove the tasks
                    for task_id in to_remove:
                        del self.tasks[task_id]
                        
                # Log if many tasks were cleaned up
                if len(to_remove) > 0:
                    logger.info(f"Cleaned up {len(to_remove)} old tasks")
                    
            except Exception as e:
                logger.error(f"Error in task cleanup: {str(e)}")
                
            # Sleep until next cleanup
            time.sleep(self.cleanup_interval)


# Singleton instance
progress_tracker = ProgressTracker()


def progress_update_callback(task_id: str) -> Callable[[Dict[str, Any]], None]:
    """
    Create a callback function for the specified task.
    
    Args:
        task_id: Task ID to update
        
    Returns:
        Callback function that updates the task
    """
    def callback(update: Dict[str, Any]):
        status = update.get("status", "running")
        progress = update.get("progress", 0)
        message = update.get("message", "Processing")
        
        progress_tracker.update_task(task_id, status, progress, message)
        
    return callback