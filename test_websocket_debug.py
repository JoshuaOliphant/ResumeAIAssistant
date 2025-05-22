#!/usr/bin/env python3

import asyncio
import websockets
import json
import requests
import time

async def test_websocket_logs():
    """Test WebSocket progress tracking with logs"""
    
    # First, create a progress task
    try:
        response = requests.post("http://localhost:5000/api/progress/create")
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data["task_id"]
            print(f"Created task: {task_id}")
        else:
            print(f"Failed to create task: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"Error creating task: {e}")
        return
    
    # Connect to WebSocket
    try:
        uri = f"ws://localhost:5000/api/progress/{task_id}/ws"
        print(f"Connecting to WebSocket: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Listen for progress updates
            timeout_count = 0
            while timeout_count < 5:  # Max 5 timeouts before giving up
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    print(f"Received: status={data.get('status')}, logs_count={len(data.get('logs', []))}")
                    if data.get('logs'):
                        print(f"Latest log: {data['logs'][-1]}")
                    
                    if data.get('status') in ['completed', 'error']:
                        break
                        
                    timeout_count = 0  # Reset timeout count on successful message
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"Timeout {timeout_count}/5 - no message received")
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
                    
    except Exception as e:
        print(f"WebSocket connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_logs())