"""
Simplified WebSocket endpoint for basic task status updates.

This module provides a minimal WebSocket interface for tracking
the status of long-running tasks like resume customization.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class StatusUpdate(BaseModel):
    """Simple status update model for WebSocket communication."""
    
    task_id: str
    status: str  # initializing, in_progress, completed, error
    message: str = "This task may take up to 20 minutes to complete. Please wait."
    error: Optional[str] = None


class ConnectionManager:
    """Manager for WebSocket connections to track task status."""
    
    def __init__(self):
        # Maps user_id -> list of websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Maps task_id -> set of user_ids that should receive updates
        self.task_subscriptions: Dict[str, Set[str]] = {}
        # Maps task_id -> latest status update
        self.latest_updates: Dict[str, StatusUpdate] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection and store it."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"New WebSocket connection for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection when it disconnects."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    def subscribe(self, task_id: str, user_id: str):
        """Subscribe a user to updates for a specific task."""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(user_id)
        logger.info(f"User {user_id} subscribed to task {task_id}")
        
        # Send the latest update for this task if available
        if task_id in self.latest_updates:
            asyncio.create_task(
                self.broadcast_to_user(
                    user_id, self.latest_updates[task_id].dict()
                )
            )
    
    async def broadcast(self, task_id: str, message: dict):
        """Broadcast a message to all users subscribed to a task."""
        if task_id not in self.task_subscriptions:
            return
        
        # Store the latest update
        if "task_id" in message and message["task_id"] == task_id:
            self.latest_updates[task_id] = StatusUpdate(**message)
        
        # Send to all subscribed users
        for user_id in self.task_subscriptions[task_id]:
            await self.broadcast_to_user(user_id, message)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a specific user."""
        if user_id not in self.active_connections:
            return
        
        connections = self.active_connections[user_id]
        if not connections:
            return
            
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {str(e)}")
                disconnected.append(websocket)
        
        # Clean up any disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket, user_id)


# Create a singleton instance
connection_manager = ConnectionManager()


async def get_user_from_token(websocket: WebSocket, db: Session):
    """Extract and validate the token from the WebSocket connection."""
    token = None
    cookies = websocket.cookies
    headers = websocket.headers
    
    # Try to get token from cookie
    if "access_token" in cookies:
        token = cookies["access_token"]
    
    # Try to get token from Authorization header
    elif "authorization" in headers:
        auth_header = headers["authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    # Try to get token from query parameter
    else:
        token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    
    try:
        user = get_current_user(token=token, db=db)
        return user
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    task_id: str, 
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for receiving status updates."""
    # Authenticate user
    user = await get_user_from_token(websocket, db)
    if not user:
        return
    
    user_id = str(user.id)
    
    # Accept connection and subscribe to task updates
    await connection_manager.connect(websocket, user_id)
    connection_manager.subscribe(task_id, user_id)
    
    try:
        # Send initial message
        initial_message = StatusUpdate(
            task_id=task_id,
            status="in_progress",
            message="This task may take up to 20 minutes to complete. Please wait."
        )
        await websocket.send_json(initial_message.dict())
        
        # Keep connection open until disconnected
        while True:
            try:
                # Wait for client messages (mostly just for ping/pong)
                data = await websocket.receive_text()
                if data and "ping" in data.lower():
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)
    except Exception:
        connection_manager.disconnect(websocket, user_id)


@router.post("/create")
async def create_task(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task for progress tracking."""
    try:
        from app.services.claude_code.progress_tracker import progress_tracker
        
        # Create a new task
        task = progress_tracker.create_task()
        
        # Log with more detail for debugging
        user_id = current_user.id if current_user else "anonymous"
        logger.info(f"Created new task {task.task_id} for user {user_id}")
        
        return {"task_id": task.task_id}
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/status/{task_id}", response_model=StatusUpdate)
async def get_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest status for a specific task."""
    try:
        from app.services.claude_code.progress_tracker import progress_tracker
        
        # Try to get task from progress tracker first
        task = progress_tracker.get_task(task_id)
        if task:
            task_dict = task.to_dict()
            return StatusUpdate(
                task_id=task_dict["task_id"],
                status=task_dict["status"],
                message=task_dict["message"],
                error=task_dict.get("error")
            )
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
    
    # Fallback to connection manager
    if task_id in connection_manager.latest_updates:
        return connection_manager.latest_updates[task_id]
    
    # If no updates yet, return default in-progress status
    return StatusUpdate(
        task_id=task_id,
        status="in_progress",
        message="This task may take up to 20 minutes to complete. Please wait."
    )