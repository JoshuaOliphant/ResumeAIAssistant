"""
Claude Code Log Streamer Module

This module implements real-time logging for Claude Code execution with support
for capturing and streaming logs to the console and to clients through websockets.
"""

import threading
import logging
import queue
import time
import asyncio
import json
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)

class ClaudeCodeLogStreamer:
    """
    Service for capturing and streaming Claude Code execution logs.
    
    This service:
    - Captures stdout/stderr from Claude Code execution
    - Streams logs to the console in real-time
    - Makes logs available via websockets for client-side display
    - Stores logs for retrieval after execution completes
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClaudeCodeLogStreamer, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the log streamer state."""
        self.task_logs: Dict[str, List[str]] = {}
        self.task_queues: Dict[str, queue.Queue] = {}
        self.active_tasks: Dict[str, threading.Thread] = {}
        self.lock = threading.RLock()
        
    def create_log_stream(self, task_id: str) -> queue.Queue:
        """
        Create a new log stream for a task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Queue to receive log messages
        """
        with self.lock:
            if task_id not in self.task_logs:
                self.task_logs[task_id] = []
            
            if task_id not in self.task_queues:
                self.task_queues[task_id] = queue.Queue()
            
            return self.task_queues[task_id]
    
    def add_log(self, task_id: str, message: str):
        """
        Add a log message to a task's log stream.
        
        Args:
            task_id: Task ID to log for
            message: Log message to add
        """
        with self.lock:
            # Create log stream if it doesn't exist
            if task_id not in self.task_logs:
                self.create_log_stream(task_id)
            
            # Add timestamp to message
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            formatted_message = f"[{timestamp}] {message}"
            
            # Store message in logs
            self.task_logs[task_id].append(formatted_message)
            
            # Put message in queue for real-time subscribers
            if task_id in self.task_queues:
                try:
                    self.task_queues[task_id].put_nowait(formatted_message)
                except queue.Full:
                    # If queue is full, remove oldest message and try again
                    try:
                        self.task_queues[task_id].get_nowait()
                        self.task_queues[task_id].put_nowait(formatted_message)
                    except (queue.Empty, queue.Full):
                        pass
    
    def get_logs(self, task_id: str) -> List[str]:
        """
        Get all logs for a task.
        
        Args:
            task_id: Task ID to get logs for
            
        Returns:
            List of log messages
        """
        with self.lock:
            return self.task_logs.get(task_id, []).copy()
    
    def clear_logs(self, task_id: str):
        """
        Clear logs for a task.
        
        Args:
            task_id: Task ID to clear logs for
        """
        with self.lock:
            if task_id in self.task_logs:
                self.task_logs[task_id] = []
    
    def cleanup_task(self, task_id: str):
        """
        Clean up resources for a task.
        
        Args:
            task_id: Task ID to clean up
        """
        with self.lock:
            if task_id in self.task_queues:
                del self.task_queues[task_id]
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    async def stream_logs(self, task_id: str) -> List[str]:
        """
        Stream logs for a task as they arrive.
        
        Args:
            task_id: Task ID to stream logs for
            
        Returns:
            AsyncGenerator yielding log messages
        """
        # Get existing logs first
        logs = self.get_logs(task_id)
        return logs
    
    def start_output_stream(self, task_id: str, process_output, output_queue: queue.Queue):
        """
        Start streaming output from a process to logs.
        
        Args:
            task_id: Task ID to stream logs for
            process_output: Output to stream (file-like object)
            output_queue: Queue to put output in
        """
        def read_output():
            try:
                for line in iter(process_output.readline, ''):
                    if line:
                        line = line.strip()
                        if line:
                            # Add to logs and put in queue
                            self.add_log(task_id, line)
                            output_queue.put(line)
                            # Print to console for real-time debugging
                            print(f"[Claude Code] {task_id}: {line}")
            except Exception as e:
                self.add_log(task_id, f"ERROR: {str(e)}")
            finally:
                output_queue.put(None)  # Signal end of stream
        
        # Create and start thread
        thread = threading.Thread(target=read_output)
        thread.daemon = True
        
        with self.lock:
            self.active_tasks[task_id] = thread
        
        thread.start()
        return thread

# Create singleton instance
log_streamer = ClaudeCodeLogStreamer()

def get_log_streamer() -> ClaudeCodeLogStreamer:
    """Get the singleton log streamer instance."""
    return log_streamer