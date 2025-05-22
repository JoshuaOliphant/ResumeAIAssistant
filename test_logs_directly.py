#!/usr/bin/env python3

import time
import asyncio
from app.services.claude_code.progress_tracker import progress_tracker
from app.services.claude_code.log_streamer import get_log_streamer

def test_logs_simulation():
    """Test if logs are properly included in task to_dict()"""
    
    # Create a task
    task = progress_tracker.create_task()
    task_id = task.task_id
    print(f"Created task: {task_id}")
    
    # Get log streamer and create log stream
    log_streamer = get_log_streamer()
    log_streamer.create_log_stream(task_id)
    
    # Add some test logs
    print("Adding test logs...")
    log_streamer.add_log(task_id, "Starting Claude Code customization")
    log_streamer.add_log(task_id, "Analyzing resume content")
    log_streamer.add_log(task_id, "Building customization prompt")
    
    # Update task status to in_progress
    task.update("in_progress", 25, "Processing customization")
    
    # Get task status with logs
    task_dict = task.to_dict()
    print(f"Task status: {task_dict['status']}")
    print(f"Task message: {task_dict['message']}")
    print(f"Logs count: {len(task_dict['logs'])}")
    
    if task_dict['logs']:
        print("Logs:")
        for i, log in enumerate(task_dict['logs']):
            print(f"  {i+1}: {log}")
    else:
        print("No logs found!")
        
    # Test direct log retrieval
    direct_logs = log_streamer.get_logs(task_id)
    print(f"Direct logs count: {len(direct_logs)}")
    
    # Clean up
    progress_tracker.tasks.pop(task_id, None)

if __name__ == "__main__":
    test_logs_simulation()