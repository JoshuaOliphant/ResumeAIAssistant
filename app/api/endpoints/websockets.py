"""
WebSocket endpoints for real-time progress updates.

This module provides WebSocket endpoints for tracking the progress
of long-running resume customization tasks.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.claude_code.progress_tracker import progress_tracker
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/customize/{task_id}")
async def websocket_customize_progress(
    websocket: WebSocket,
    task_id: str
):
    """
    WebSocket endpoint for tracking resume customization progress.
    
    Args:
        websocket: WebSocket connection
        task_id: ID of the task to track
    """
    await websocket.accept()
    
    try:
        # Retrieve task from progress tracker
        task = progress_tracker.get_task(task_id)
        
        if not task:
            await websocket.send_json({"error": "Task not found"})
            await websocket.close()
            return
        
        # Create a queue for receiving updates
        queue = asyncio.Queue()
        
        # Subscribe to task progress updates
        task.add_subscriber(queue)
        
        # Send initial status
        await websocket.send_json(task.to_dict())
        
        # Set up ping interval
        ping_interval = settings.WS_PING_INTERVAL
        last_ping = asyncio.get_event_loop().time()
        
        # Process updates
        try:
            while True:
                # Wait for either a progress update or ping timeout
                try:
                    # Wait for a message with a timeout
                    update_task = asyncio.create_task(queue.get())
                    
                    # Set up a timeout task
                    current_time = asyncio.get_event_loop().time()
                    time_since_last_ping = current_time - last_ping
                    timeout = max(0.1, ping_interval - time_since_last_ping)
                    
                    timeout_task = asyncio.create_task(asyncio.sleep(timeout))
                    
                    # Wait for either task to complete
                    done, pending = await asyncio.wait(
                        [update_task, timeout_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel the pending task
                    for task in pending:
                        task.cancel()
                    
                    # If we got an update, send it
                    if update_task in done:
                        progress = await update_task
                        await websocket.send_json(progress)
                        
                        # If task is complete or errored, break the loop
                        if progress["status"] in ["completed", "error"]:
                            break
                    
                    # If we hit the timeout, send a ping
                    if timeout_task in done:
                        await websocket.ping()
                        last_ping = asyncio.get_event_loop().time()
                
                except asyncio.CancelledError:
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for task {task_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket for task {task_id}: {str(e)}")
            await websocket.send_json({"error": str(e)})
        finally:
            # Unsubscribe from updates when connection is closed
            task.remove_subscriber(queue)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during setup for task {task_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket setup for task {task_id}: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except:
            pass


@router.websocket("/ws/customize/all")
async def websocket_all_tasks(
    websocket: WebSocket,
    status: Optional[str] = None
):
    """
    WebSocket endpoint for tracking all customization tasks.
    
    Args:
        websocket: WebSocket connection
        status: Optional filter for task status
    """
    await websocket.accept()
    
    try:
        # Set up ping interval
        ping_interval = settings.WS_PING_INTERVAL
        last_ping = asyncio.get_event_loop().time()
        
        # Send initial task list
        tasks = progress_tracker.list_tasks(status)
        await websocket.send_json({"type": "tasks", "data": tasks})
        
        # Process updates
        while True:
            # Wait for ping timeout
            current_time = asyncio.get_event_loop().time()
            time_since_last_ping = current_time - last_ping
            timeout = max(0.1, ping_interval - time_since_last_ping)
            
            try:
                # Wait for timeout
                await asyncio.sleep(timeout)
                
                # Send ping
                await websocket.ping()
                last_ping = asyncio.get_event_loop().time()
                
                # Send updated task list
                tasks = progress_tracker.list_tasks(status)
                await websocket.send_json({"type": "tasks", "data": tasks})
                
            except asyncio.CancelledError:
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for all tasks view")
    except Exception as e:
        logger.error(f"Error in WebSocket for all tasks view: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except:
            pass