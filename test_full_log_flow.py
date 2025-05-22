#!/usr/bin/env python3

import asyncio
import time
from app.services.claude_code.progress_tracker import progress_tracker
from app.services.claude_code.log_streamer import get_log_streamer

async def test_full_log_flow():
    """Test the complete flow from log addition to subscriber notification"""
    
    # Create a task
    task = progress_tracker.create_task()
    task_id = task.task_id
    print(f"Created task: {task_id}")
    
    # Create a queue to simulate WebSocket subscriber
    subscriber_queue = asyncio.Queue()
    
    # Subscribe to task updates (like WebSocket does)
    task.add_subscriber(subscriber_queue)
    print("Added subscriber to task")
    
    # Get initial status
    initial_status = task.to_dict()
    print(f"Initial status: logs={len(initial_status['logs'])}, message='{initial_status['message']}'")
    
    # Get log streamer and create log stream
    log_streamer = get_log_streamer()
    log_streamer.create_log_stream(task_id)
    print("Created log stream")
    
    # Add logs using the log streamer (this should trigger notifications)
    print("\nAdding logs...")
    log_streamer.add_log(task_id, "Starting Claude Code customization")
    log_streamer.add_log(task_id, "Analyzing resume content")
    log_streamer.add_log(task_id, "Building customization prompt")
    
    # Check if we received any notifications
    notifications_received = 0
    try:
        while True:
            # Wait for notification with short timeout
            notification = await asyncio.wait_for(subscriber_queue.get(), timeout=1.0)
            notifications_received += 1
            print(f"Notification {notifications_received}: status={notification['status']}, logs={len(notification['logs'])}, message='{notification['message']}'")
            if notification['logs']:
                print(f"  Latest log: {notification['logs'][-1]}")
    except asyncio.TimeoutError:
        print(f"No more notifications (received {notifications_received} total)")
    
    # Get final status directly
    final_status = task.to_dict()
    print(f"\nFinal status: logs={len(final_status['logs'])}, message='{final_status['message']}'")
    
    # Clean up
    progress_tracker.tasks.pop(task_id, None)
    
    return notifications_received > 0

if __name__ == "__main__":
    success = asyncio.run(test_full_log_flow())
    print(f"\nTest {'PASSED' if success else 'FAILED'}: {'Notifications received' if success else 'No notifications received'}")