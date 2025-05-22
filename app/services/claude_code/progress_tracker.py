"""
Enhanced Progress Tracking System for Claude Code Resume Customization

This module implements a comprehensive task tracking system for long-running
Claude Code customization tasks, supporting detailed progress updates with
percentage completion and status messages.
"""

import time
import uuid
import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)

class Task:
    """
    Represents a running customization task with detailed progress tracking.
    """
    def __init__(self, task_id: str):
        """
        Initialize a tracked task.
        
        Args:
            task_id: Unique identifier for the task
        """
        self._task_id = task_id
        self.status = "initializing"  # initializing, in_progress, completed, error
        self.created_at = time.time()
        self.updated_at = time.time()
        self.result = None
        self.error = None
        self.progress = 0  # Progress percentage (0-100)
        self.message = "Task is starting..."  # Detailed status message
        self.subscribers: Set[asyncio.Queue] = set()
        
    @property
    def task_id(self) -> str:
        """Get the task ID"""
        return self._task_id
        
    @task_id.setter
    def task_id(self, value: str):
        """
        Set the task ID and ensure it's properly registered in the tracker.
        """
        # Skip if value is the same
        if value == self._task_id:
            return
            
        old_id = self._task_id
        self._task_id = value
        
        # Get tracker singleton to update the task registry
        tracker = progress_tracker
        
        # Update the tasks dictionary to use the new ID
        with tracker.lock:
            # Remove the old entry if it exists
            if old_id in tracker.tasks and tracker.tasks[old_id] == self:
                del tracker.tasks[old_id]
                
            # Add with new ID
            tracker.tasks[value] = self
            logger.info(f"Task ID updated from {old_id} to {value}, total tasks: {len(tracker.tasks)}")
        
    def update(self, status: str, progress: Optional[int] = None, message: Optional[str] = None):
        """
        Update the task status and notify subscribers.
        
        Args:
            status: Current status of the task
            progress: Progress percentage (0-100), optional
            message: Detailed status message, optional
        """
        # Validate status parameter
        valid_statuses = ["initializing", "in_progress", "completed", "error", "queued", "pending"]
        if status not in valid_statuses:
            logger.warning(f"Task {self.task_id}: Invalid status '{status}', using 'in_progress'")
            status = "in_progress"
            
        self.status = status
        self.updated_at = time.time()
        
        # Update progress if provided
        if progress is not None:
            # Ensure progress is an integer and within valid range
            try:
                progress_int = int(progress)
                self.progress = max(0, min(100, progress_int))  # Clamp to 0-100 range
            except (ValueError, TypeError):
                logger.warning(f"Task {self.task_id}: Invalid progress value '{progress}', keeping current value")
        
        # Update message if provided
        if message is not None:
            # Ensure message is a string
            self.message = str(message) if message is not None else self.message
        
        # Auto-update progress based on status if not explicitly provided
        if progress is None:
            if status == "completed":
                self.progress = 100
            elif status == "initializing" or status == "queued":
                self.progress = 0
            elif status == "error":
                # Keep current progress for error status
                pass
        
        # Notify all subscribers of the update
        for queue in list(self.subscribers):
            try:
                if not queue.full():
                    queue.put_nowait(self.to_dict())
            except Exception as e:
                logger.error(f"Error notifying subscriber for task {self.task_id}: {str(e)}")
                
    def process_log(self, log_message: str):
        """
        Process a log message to check for completion, errors, and update progress.
        
        Args:
            log_message: The log message to check
        """
        # Update status to in_progress if we're getting logs and not yet started
        if self.status == "initializing":
            self.status = "in_progress"
            self.updated_at = time.time()
        
        # Update message with latest log for real-time feedback
        if log_message and len(log_message.strip()) > 0:
            # Use the latest log message as the current status message
            self.message = log_message.strip()
            self.updated_at = time.time()
        
        # Check for error indicators
        if "error" in log_message.lower():
            if "fatal error" in log_message.lower() or "critical error" in log_message.lower():
                self.status = "error"
                self.error = log_message
                self.updated_at = time.time()
                self.notify_subscribers()
                return
        
        # Check for completion
        elif "execution completed successfully" in log_message.lower() or "completed successfully" in log_message.lower():
            self.status = "completed"
            self.progress = 100
            self.message = "Resume customization completed successfully"
            self.updated_at = time.time()
            self.notify_subscribers()
            return
            
        # Estimate progress based on log content patterns
        if self.status == "in_progress":
            progress_estimate = self._estimate_progress_from_log(log_message)
            if progress_estimate > self.progress:
                self.progress = progress_estimate
        
        # Notify subscribers of any update
        self.notify_subscribers()
        
    def _estimate_progress_from_log(self, log_message: str) -> int:
        """
        Estimate progress percentage based on log message content.
        
        Args:
            log_message: The log message to analyze
            
        Returns:
            Estimated progress percentage (0-100)
        """
        message_lower = log_message.lower()
        
        # Starting phase
        if any(phrase in message_lower for phrase in ["starting", "initializing", "preparing"]):
            return max(5, self.progress)
        
        # Analysis/processing phase
        elif any(phrase in message_lower for phrase in ["analyzing", "processing", "building prompt"]):
            return max(15, self.progress)
            
        # Execution phase
        elif any(phrase in message_lower for phrase in ["executing", "running", "claude code"]):
            return max(25, self.progress)
            
        # Output processing
        elif any(phrase in message_lower for phrase in ["output", "content", "generating"]):
            return max(60, self.progress)
            
        # Saving/finishing
        elif any(phrase in message_lower for phrase in ["saving", "writing", "finalizing"]):
            return max(85, self.progress)
            
        # Default incremental progress for any activity
        else:
            return min(95, self.progress + 2)  # Slow incremental progress, never reach 100 until completion
            
    def notify_subscribers(self):
        """Notify all subscribers about task updates"""
        for queue in list(self.subscribers):
            try:
                if not queue.full():
                    queue.put_nowait(self.to_dict())
            except Exception as e:
                logger.error(f"Error notifying subscriber for task {self.task_id}: {str(e)}")
    
    def add_subscriber(self, queue: asyncio.Queue):
        """
        Add a subscriber to receive status updates.
        
        Args:
            queue: AsyncIO queue to receive updates
        """
        self.subscribers.add(queue)
        queue.put_nowait(self.to_dict())  # Send current status immediately
        
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
            Dictionary containing detailed task status information including logs
        """
        # Get logs from log streamer
        try:
            from app.services.claude_code.log_streamer import get_log_streamer
            log_streamer = get_log_streamer()
            logs = log_streamer.get_logs(self.task_id)
        except Exception:
            logs = []
            
        return {
            "task_id": self.task_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "message": self.message or "This task may take up to 20 minutes to complete. Please wait.",
            "logs": logs  # Include logs in the status update
        }
    
    def update_progress(self, progress: int, message: Optional[str] = None):
        """
        Update only the progress percentage and optionally the message.
        
        Args:
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        self.progress = max(0, min(100, progress))  # Clamp to 0-100 range
        self.updated_at = time.time()
        
        if message is not None:
            self.message = message
        
        # Notify subscribers
        for queue in list(self.subscribers):
            try:
                if not queue.full():
                    queue.put_nowait(self.to_dict())
            except Exception as e:
                logger.error(f"Error notifying subscriber for task {self.task_id}: {str(e)}")
    
    def update_message(self, message: str):
        """
        Update only the status message.
        
        Args:
            message: New status message
        """
        self.message = message
        self.updated_at = time.time()
        
        # Notify subscribers
        for queue in list(self.subscribers):
            try:
                if not queue.full():
                    queue.put_nowait(self.to_dict())
            except Exception as e:
                logger.error(f"Error notifying subscriber for task {self.task_id}: {str(e)}")
    
    def set_result(self, result: Dict[str, Any]):
        """
        Set the final result of the task.
        
        Args:
            result: Task result data
        """
        self.result = result
        self.update("completed", progress=100, message="Task completed successfully")
    
    def set_error(self, error: str):
        """
        Set an error status for the task.
        
        Args:
            error: Error message
        """
        self.error = str(error) if error else "Unknown error"
        self.update("error", message=f"Task failed: {self.error}")


class ProgressTracker:
    """
    Singleton task tracking service that manages task status
    and handles subscriptions to status updates.
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
            
    def process_log(self, task_id: str, log_message: str):
        """
        Process a log message to check for completion or errors.
        
        Args:
            task_id: ID of the task associated with the log
            log_message: Log message to process
        """
        task = self.get_task(task_id)
        if task:
            task.process_log(log_message)
            return True
        return False
    
    def update_task(self, task_id: str, status: str, progress: Optional[int] = None, message: Optional[str] = None) -> bool:
        """
        Update a task's status, progress, and/or message.
        
        Args:
            task_id: Task to update
            status: New status
            progress: Progress percentage (0-100), optional
            message: Detailed status message, optional
            
        Returns:
            True if task was found and updated, False otherwise
        """
        task = self.get_task(task_id)
        if task:
            task.update(status, progress, message)
            logger.debug(f"Updated task {task_id}: status={status}, progress={progress}, message={message}")
            return True
        else:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return False
    
    def update_task_progress(self, task_id: str, progress: int, message: Optional[str] = None) -> bool:
        """
        Update a task's progress percentage and optionally the message.
        
        Args:
            task_id: Task to update
            progress: Progress percentage (0-100)
            message: Optional status message
            
        Returns:
            True if task was found and updated, False otherwise
        """
        task = self.get_task(task_id)
        if task:
            task.update_progress(progress, message)
            logger.debug(f"Updated task {task_id} progress: {progress}% - {message}")
            return True
        else:
            logger.warning(f"Attempted to update progress for non-existent task: {task_id}")
            return False
    
    def update_task_message(self, task_id: str, message: str) -> bool:
        """
        Update a task's status message.
        
        Args:
            task_id: Task to update
            message: New status message
            
        Returns:
            True if task was found and updated, False otherwise
        """
        task = self.get_task(task_id)
        if task:
            task.update_message(message)
            logger.debug(f"Updated task {task_id} message: {message}")
            return True
        else:
            logger.warning(f"Attempted to update message for non-existent task: {task_id}")
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