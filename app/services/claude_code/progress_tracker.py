"""
Progress Tracking System for Claude Code Resume Customization

This module implements a streamlined task tracking system for long-running
Claude Code customization tasks, focusing on providing real-time log
updates to clients rather than artificial progress estimation.
"""

import time
import uuid
import logging
import asyncio
import threading
import re
import queue
from typing import Dict, Any, List, Optional, Callable, Set

logger = logging.getLogger(__name__)

class Task:
    """
    Represents a running customization task with log-based progress tracking.
    
    This updated implementation focuses on parsing Claude Code logs to extract
    natural progress indicators rather than using artificial progress stages.
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
        
        # New attributes for smarter progress tracking
        self.logged_todos = []       # Track todo items from Claude Code
        self.completed_todos = []    # Track completed todo items
        self.current_todo = None     # Current in-progress todo item
        self.total_todos = 0         # Total number of todos detected
        
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
                
    def update_from_log(self, log_message: str):
        """
        Update task status based on log message content.
        
        This method parses Claude Code logs to extract progress information
        from todo lists, status markers, and other content patterns.
        
        Args:
            log_message: The log message to parse
        """
        try:
            # If we already have an error, don't update from logs
            if self.status == "error":
                return
                
            # Check for error indicators
            if "error" in log_message.lower():
                if "fatal error" in log_message.lower() or "critical error" in log_message.lower():
                    self.status = "error"
                    self.message = log_message
                    self.error = log_message
                    self.updated_at = time.time()
                    self.notify_subscribers()
                    return
            
            # Pattern 1: Check for todo list creation
            todo_list_match = re.search(r'Adding the following todos to the todo list:(.*?)(?:\n\n|$)', log_message, re.DOTALL)
            if todo_list_match:
                # Process new todo list
                todo_text = todo_list_match.group(1)
                todos = re.findall(r'\d+\.\s+(.*?)(?:\n|$)', todo_text)
                
                if todos:
                    self.logged_todos = todos
                    self.total_todos = len(todos)
                    self.progress = 5  # Just starting with todos
                    self.message = f"Planning task: identified {len(todos)} steps"
                    self.notify_subscribers()
                    return
            
            # Pattern 2: Check for todo status changes
            todo_status_match = re.search(r'marking (the .+? todo|todo \d+) as (in_progress|completed)', log_message, re.IGNORECASE)
            if todo_status_match:
                todo_ref = todo_status_match.group(1)
                status = todo_status_match.group(2)
                
                if status == "in_progress":
                    # Extract the todo item being worked on
                    todo_number_match = re.search(r'todo (\d+)', todo_ref)
                    if todo_number_match and self.logged_todos:
                        todo_index = int(todo_number_match.group(1)) - 1
                        if 0 <= todo_index < len(self.logged_todos):
                            self.current_todo = self.logged_todos[todo_index]
                    elif "first" in todo_ref and self.logged_todos:
                        self.current_todo = self.logged_todos[0]
                        
                    # Update status message
                    if self.current_todo:
                        self.message = f"Working on: {self.current_todo}"
                
                elif status == "completed":
                    # Mark current todo as completed
                    if self.current_todo and self.current_todo not in self.completed_todos:
                        self.completed_todos.append(self.current_todo)
                        
                    # Also check if a specific todo was referenced
                    todo_number_match = re.search(r'todo (\d+)', todo_ref)
                    if todo_number_match and self.logged_todos:
                        todo_index = int(todo_number_match.group(1)) - 1
                        if 0 <= todo_index < len(self.logged_todos):
                            completed_todo = self.logged_todos[todo_index]
                            if completed_todo not in self.completed_todos:
                                self.completed_todos.append(completed_todo)
                
                # Calculate new progress percentage
                if self.total_todos > 0:
                    # Use completed todos to calculate progress between 10-90%
                    todo_progress = len(self.completed_todos) / self.total_todos
                    self.progress = 10 + int(todo_progress * 80)
                
                self.updated_at = time.time()
                self.notify_subscribers()
                return
            
            # Pattern 3: Check for output file generation
            if "customized resume" in log_message.lower() and "wrote" in log_message.lower():
                self.progress = min(95, self.progress + 5)
                self.message = "Generated customized resume"
                self.updated_at = time.time()
                self.notify_subscribers()
                return
                
            if "customization summary" in log_message.lower() and "wrote" in log_message.lower():
                self.progress = min(99, self.progress + 4)
                self.message = "Generated customization summary"
                self.updated_at = time.time()
                self.notify_subscribers()
                return
            
            # Pattern 4: Check for completion
            if "execution completed successfully" in log_message.lower():
                self.status = "completed"
                self.progress = 100
                self.message = "Customization complete"
                self.updated_at = time.time()
                self.notify_subscribers()
                return
                
            # Pattern 5: Check for general progress indicators
            if "progress" in log_message.lower():
                progress_match = re.search(r'Progress: (.+?)(?:\((\d+)%\))?', log_message)
                if progress_match:
                    message = progress_match.group(1).strip()
                    
                    # Try to extract percentage if provided
                    if progress_match.group(2):
                        pct = int(progress_match.group(2))
                        # Only use percentage if it's greater than current
                        if pct > self.progress:
                            self.progress = pct
                    
                    self.message = message
                    self.updated_at = time.time()
                    self.notify_subscribers()
                    return
                    
        except Exception as e:
            logger.error(f"Error updating task {self.task_id} from log: {str(e)}")
            
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
            Dictionary containing task status information including todos
        """
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "todos": {
                "total": self.total_todos,
                "completed": len(self.completed_todos),
                "completed_items": self.completed_todos,
                "all_items": self.logged_todos,
                "current_item": self.current_todo
            }
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
    
    This updated version uses Claude Code logs to infer progress 
    instead of artificial estimation.
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
        
        # Register for log updates
        self._register_log_handlers()
    
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
    
    def _register_log_handlers(self):
        """
        Register for log updates from Claude Code log streamer.
        
        This sets up a connection to process logs for progress tracking.
        """
        # Import here to avoid circular imports
        try:
            # We'll use a deferred import approach
            self._log_handler_registered = False
            logger.info("Log handlers will be registered when first needed")
        except Exception as e:
            logger.error(f"Error setting up log handlers: {str(e)}")
            
    def process_log(self, task_id: str, log_message: str):
        """
        Process a log message to update task progress.
        
        Args:
            task_id: ID of the task associated with the log
            log_message: Log message to process
            
        Returns:
            True if the task was updated, False otherwise
        """
        task = self.get_task(task_id)
        if task:
            # Update task based on log content patterns
            task.update_from_log(log_message)
            return True
        return False
    
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