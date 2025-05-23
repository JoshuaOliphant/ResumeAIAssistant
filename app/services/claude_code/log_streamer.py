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
import re
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
    
    def add_log(self, task_id: str, message: str, level: str = "info", metadata: Dict[str, Any] = None):
        """
        Add a log message to a task's log stream.
        
        Args:
            task_id: Task ID to log for
            message: Log message to add
            level: Log level ("info", "warning", "error", "debug")
            metadata: Optional additional structured data
        """
        with self.lock:
            # Create log stream if it doesn't exist
            if task_id not in self.task_logs:
                self.create_log_stream(task_id)
            
            # Add timestamp to message
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            
            # Format the message based on log level
            level_prefix = ""
            if level == "error":
                level_prefix = "[ERROR] "
            elif level == "warning":
                level_prefix = "[WARNING] "
            elif level == "debug":
                level_prefix = "[DEBUG] "
                
            formatted_message = f"[{timestamp}] {level_prefix}{message}"
            
            # Build structured log object
            log_entry = {
                "timestamp": timestamp,
                "message": message,
                "formatted_message": formatted_message,
                "level": level
            }
            
            # Add metadata if provided
            if metadata:
                log_entry["metadata"] = metadata
            
            # Determine if we should store/send structured or simple logs
            # Based on whether subscribers might expect structured data
            output_message = log_entry if metadata else formatted_message
            
            # Store message in logs (always store the formatted string for simplicity)
            self.task_logs[task_id].append(formatted_message)
            
            # Put message in queue for real-time subscribers
            if task_id in self.task_queues:
                try:
                    self.task_queues[task_id].put_nowait(output_message)
                except queue.Full:
                    # If queue is full, remove oldest message and try again
                    try:
                        self.task_queues[task_id].get_nowait()
                        self.task_queues[task_id].put_nowait(output_message)
                    except (queue.Empty, queue.Full):
                        pass
                        
            # Log to application logger for critical levels
            if level == "error":
                logger.error(f"Task {task_id}: {message}")
            elif level == "warning":
                logger.warning(f"Task {task_id}: {message}")
                
            # Update progress tracker based on this log message
            try:
                # Deferred import to avoid circular imports
                from app.services.claude_code.progress_tracker import progress_tracker
                progress_tracker.process_log(task_id, message)
            except Exception as e:
                # Just log it but don't interrupt the main flow
                logger.error(f"Error updating progress from log: {str(e)}")
    
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
    
    async def stream_logs(self, task_id: str, timeout: int = 3600):
        """
        Stream logs for a task as they arrive.
        
        Args:
            task_id: Task ID to stream logs for
            timeout: Maximum time to stream logs in seconds (default: 1 hour)
            
        Yields:
            Log messages as they arrive
        """
        # Create a queue for new log messages
        log_queue = asyncio.Queue(maxsize=100)
        
        # Get existing logs first
        initial_logs = self.get_logs(task_id)
        
        # Function to monitor logs and put them in the async queue
        def monitor_logs():
            try:
                # Create a queue for this thread
                q = queue.Queue()
                
                # Create a thread-safe queue in the log streamer
                with self.lock:
                    if task_id not in self.task_queues:
                        self.task_queues[task_id] = q
                    else:
                        q = self.task_queues[task_id]
                
                # Monitor the queue for new logs
                while True:
                    try:
                        # Wait for a log message with timeout
                        message = q.get(timeout=1)
                        
                        # Put the message in the async queue
                        # This will be awaited by the event loop
                        asyncio.run_coroutine_threadsafe(
                            log_queue.put(message),
                            asyncio.get_event_loop()
                        )
                    except queue.Empty:
                        # Check if we should stop monitoring
                        if getattr(monitor_thread, "stop_flag", False):
                            break
                        continue
            except Exception as e:
                logger.error(f"Error in log monitor thread: {str(e)}")
                
                # Try to put error in async queue
                try:
                    asyncio.run_coroutine_threadsafe(
                        log_queue.put(f"ERROR: {str(e)}"),
                        asyncio.get_event_loop()
                    )
                except:
                    pass
        
        # Start monitor thread
        monitor_thread = threading.Thread(target=monitor_logs)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            # First, yield all existing logs
            for log in initial_logs:
                yield log
            
            # Start time for timeout tracking
            start_time = time.time()
            
            # Then yield new logs as they arrive
            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    yield f"Streaming timeout after {timeout} seconds"
                    break
                
                try:
                    # Wait for a new log message with a short timeout
                    message = await asyncio.wait_for(log_queue.get(), timeout=1)
                    
                    # Yield the message
                    yield message
                    
                    # Mark as done
                    log_queue.task_done()
                except asyncio.TimeoutError:
                    # Check if the task is still active
                    from app.services.claude_code.progress_tracker import progress_tracker
                    task = progress_tracker.get_task(task_id)
                    
                    # If the task is done or errored, stop streaming
                    if task and task.status in ["completed", "error"]:
                        break
                    
                    # Otherwise, continue waiting for new logs
                    continue
        finally:
            # Signal the monitor thread to stop
            monitor_thread.stop_flag = True
            
            # Wait for the monitor thread to finish
            try:
                monitor_thread.join(timeout=2)
            except:
                pass
    
    def start_output_stream(self, task_id: str, process_output, output_queue: queue.Queue, stream_type: str = "stdout"):
        """
        Start streaming output from a process to logs.
        
        Args:
            task_id: Task ID to stream logs for
            process_output: Output to stream (file-like object)
            output_queue: Queue to put output in
            stream_type: Type of stream ("stdout" or "stderr")
            
        Returns:
            Thread that is reading the output
        """
        def read_output():
            buffer = []
            is_error_stream = stream_type == "stderr"
            default_level = "warning" if is_error_stream else "info"
    
            try:
                # Different reading approach based on stream type
                if is_error_stream:
                    # For stderr, we treat all output as potential errors/warnings
                    for line in iter(process_output.readline, b''):
                        if not line:
                            continue
                    
                        # Convert bytes to string if needed
                        if isinstance(line, bytes):
                            line = line.decode('utf-8', errors='replace')
                    
                        line = line.strip()
                        if not line:
                            continue
                    
                        # Determine log level based on content
                        log_level = "warning"
                        if "error" in line.lower() or "exception" in line.lower():
                            log_level = "error"
                    
                        # Add to logs and queue
                        self.add_log(task_id, line, level=log_level)
                        output_queue.put(line)
                
                    # Signal end of stream
                    output_queue.put(None)
                    return
                
                # For stdout, use chunked reading for better handling of stream-json
                while True:
                    # Read a chunk - this handles partial lines better
                    chunk = process_output.read(4096)
                    
                    # Break if we're at the end of the stream (empty chunk)
                    if not chunk:
                        # Process any remaining data in buffer
                        if buffer:
                            final_line = ''.join(buffer).strip()
                            if final_line:
                                self.add_log(task_id, final_line, level=default_level)
                                output_queue.put(final_line)
                        break
                    
                    # Split the chunk into lines, keeping any partial line
                    lines = chunk.split('\n')
                    
                    # If we have a buffer from a previous partial line, combine with the first line
                    if buffer:
                        lines[0] = ''.join(buffer) + lines[0]
                        buffer = []
                    
                    # If the chunk doesn't end with a newline, the last line is partial
                    if not chunk.endswith('\n'):
                        buffer = [lines.pop()]
                    
                    # Process complete lines
                    for line in lines:
                        line = line.strip()
                        if line:
                            # Determine log level based on line content and stream type
                            log_level = default_level
                            if stream_type == "stdout":
                                # For stdout stream, infer level from content
                                if "error" in line.lower() or "exception" in line.lower():
                                    log_level = "error"
                                elif "warning" in line.lower() or "warn" in line.lower():
                                    log_level = "warning"
                                elif "debug" in line.lower():
                                    log_level = "debug"
                                
                                # Also look for JSON content with status indicators
                                if line.startswith("{") and line.endswith("}"):
                                    try:
                                        data = json.loads(line)
                                        if isinstance(data, dict):
                                            # If it has an error field, treat as error
                                            if "error" in data or data.get("status") == "error":
                                                log_level = "error"
                                            # If it's a warning, treat as warning
                                            elif data.get("status") == "warning":
                                                log_level = "warning"
                                    except:
                                        pass
                                
                            # Extract any structured data if possible
                            metadata = None
                            try:
                                # Check if the line contains JSON
                                if '{' in line and '}' in line:
                                    json_match = re.search(r'({.*})', line)
                                    if json_match:
                                        try:
                                            json_data = json.loads(json_match.group(1))
                                            # Extract the actual message and metadata
                                            if isinstance(json_data, dict):
                                                # Use the JSON data as metadata
                                                metadata = json_data
                                                # If the JSON has a message field, extract it
                                                if "message" in json_data:
                                                    line = json_data["message"]
                                        except:
                                            # If JSON parsing fails, just use the original line
                                            pass
                            except:
                                # If any exception occurs in JSON parsing, just use original line
                                pass
                                
                            # Add to logs with appropriate level
                            self.add_log(task_id, line, level=log_level, metadata=metadata)
                            
                            # Put in output queue
                            output_queue.put(line)
                            
                            # Print to console for real-time debugging
                            level_prefix = ""
                            if log_level == "error":
                                level_prefix = "[ERROR] "
                            elif log_level == "warning":
                                level_prefix = "[WARNING] "
                                
                            print(f"[Claude Code] {task_id}: {level_prefix}{line}")
                            
                            # Flush stdout to ensure real-time visibility in logs
                            import sys
                            sys.stdout.flush()
            except Exception as e:
                error_msg = f"ERROR in log streaming: {str(e)}"
                self.add_log(task_id, error_msg)
                logger.error(f"Error in output stream thread for task {task_id}: {str(e)}")
                
                # Try to put the error in the queue to signal the problem
                try:
                    output_queue.put(error_msg)
                except:
                    pass
            finally:
                # Signal end of stream
                try:
                    output_queue.put(None)
                except:
                    pass
                
                # Log completion
                logger.info(f"Output stream thread for task {task_id} completed")
        
        # Create and start thread with a descriptive name
        thread = threading.Thread(
            target=read_output,
            name=f"log-stream-{task_id}-{id(process_output)}"
        )
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
