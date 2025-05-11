"""
WebSocket endpoint for real-time progress updates.

This module provides both WebSocket and REST endpoints for tracking
progress of long-running operations like resume customization.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class ProgressStage(BaseModel):
    """Represents a stage in a multi-stage process with its own progress tracking."""
    
    name: str
    description: str
    progress: float = Field(0.0, ge=0.0, le=1.0)
    status: str = "pending"  # pending, in_progress, completed, error
    message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None  # in seconds


class ProgressUpdate(BaseModel):
    """Progress update model for both WebSocket and REST API."""
    
    task_id: str
    overall_progress: float = Field(0.0, ge=0.0, le=1.0)
    status: str = "in_progress"  # initializing, in_progress, completed, error
    current_stage: Optional[str] = None
    stages: Dict[str, ProgressStage] = {}
    message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None  # in seconds
    started_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProgressConnectionManager:
    """Manager for WebSocket connections to track progress updates."""
    
    def __init__(self):
        # Maps user_id -> list of websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Maps task_id -> set of user_ids that should receive updates
        self.task_subscriptions: Dict[str, Set[str]] = {}
        # Maps task_id -> latest progress update
        self.latest_updates: Dict[str, ProgressUpdate] = {}
    
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
    
    def unsubscribe(self, task_id: str, user_id: str):
        """Unsubscribe a user from updates for a specific task."""
        if task_id in self.task_subscriptions and user_id in self.task_subscriptions[task_id]:
            self.task_subscriptions[task_id].remove(user_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
            logger.info(f"User {user_id} unsubscribed from task {task_id}")
    
    async def broadcast(self, task_id: str, message: dict):
        """Broadcast a message to all users subscribed to a task."""
        if task_id not in self.task_subscriptions:
            return
        
        # Store the latest update
        if "task_id" in message and message["task_id"] == task_id:
            self.latest_updates[task_id] = ProgressUpdate(**message)
        
        # Send to all subscribed users
        for user_id in self.task_subscriptions[task_id]:
            await self.broadcast_to_user(user_id, message)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a specific user."""
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return
        
        connections = self.active_connections[user_id]
        if not connections:
            logger.debug(f"Empty connections list for user {user_id}")
            return
            
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.debug(f"Message sent to user {user_id}")
            except RuntimeError as e:
                # Connection already closed
                logger.warning(f"RuntimeError sending to WebSocket: {str(e)}")
                disconnected.append(websocket)
            except ConnectionRefusedError:
                logger.warning(f"Connection refused for user {user_id}")
                disconnected.append(websocket)
            except ConnectionResetError:
                logger.warning(f"Connection reset for user {user_id}")
                disconnected.append(websocket)
            except Exception as e:
                # Catch all other exceptions to prevent broadcast failures
                logger.error(f"Unexpected error sending message to user {user_id}: {str(e)}")
                disconnected.append(websocket)
        
        # Clean up any disconnected sockets
        for websocket in disconnected:
            logger.info(f"Cleaning up disconnected WebSocket for user {user_id}")
            self.disconnect(websocket, user_id)


# Create a singleton instance
connection_manager = ProgressConnectionManager()


async def get_user_from_token(websocket: WebSocket, db: Session):
    """Extract and validate the token from the WebSocket connection."""
    token = None
    cookies = websocket.cookies
    headers = websocket.headers
    
    # Try to get token from cookie
    if "access_token" in cookies:
        token = cookies["access_token"]
        logger.debug("Found token in cookies")
    
    # Try to get token from Authorization header
    elif "authorization" in headers:
        auth_header = headers["authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            logger.debug("Found token in authorization header")
    
    # Try to get token from query parameter
    else:
        token = websocket.query_params.get("token")
        if token:
            logger.debug("Found token in query parameters")
    
    if not token:
        logger.warning("No authentication token found in WebSocket connection")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token missing")
        return None
    
    try:
        user = get_current_user(token=token, db=db)
        logger.info(f"WebSocket authenticated for user ID: {user.id}")
        return user
    except HTTPException as e:
        logger.warning(f"Authentication failed: {str(e.detail)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Server error during authentication")
        return None


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    task_id: str, 
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for receiving real-time progress updates."""
    # Validate task_id format
    if not task_id or len(task_id) < 3:
        logger.warning(f"Invalid task_id format: {task_id}")
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Invalid task ID format")
        return
        
    # Authenticate user
    user = await get_user_from_token(websocket, db)
    if not user:
        logger.warning(f"Authentication failed for WebSocket connection to task {task_id}")
        return
    
    user_id = str(user.id)
    logger.info(f"User {user_id} connecting to WebSocket for task {task_id}")
    
    # Accept connection and subscribe to task updates
    await connection_manager.connect(websocket, user_id)
    connection_manager.subscribe(task_id, user_id)
    
    try:
        while True:
            # Wait for messages - these could be used for bidirectional communication
            # like subscribing to different tasks or requesting status updates
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.debug(f"Received WebSocket message from user {user_id}: {message}")
                
                if "type" in message:
                    if message["type"] == "subscribe" and "task_id" in message:
                        new_task_id = message["task_id"]
                        if new_task_id and len(new_task_id) >= 3:
                            connection_manager.subscribe(new_task_id, user_id)
                            logger.info(f"User {user_id} subscribed to additional task {new_task_id}")
                        else:
                            logger.warning(f"Invalid task_id in subscribe message: {new_task_id}")
                            
                    elif message["type"] == "unsubscribe" and "task_id" in message:
                        unsub_task_id = message["task_id"]
                        connection_manager.unsubscribe(unsub_task_id, user_id)
                        logger.info(f"User {user_id} unsubscribed from task {unsub_task_id}")
                        
                    elif message["type"] == "ping":
                        # Handle ping messages to keep connection alive
                        await websocket.send_json({"type": "pong", "timestamp": message.get("timestamp")})
                        
                    else:
                        logger.warning(f"Unknown message type: {message['type']}")
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from client: {e}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id} and task {task_id}")
        connection_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {str(e)}")
        connection_manager.disconnect(websocket, user_id)


@router.post("/update", response_model=ProgressUpdate)
async def update_progress(
    update: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update progress for a specific task and broadcast to subscribed clients."""
    # In a production app, you might want to verify that the user has permission
    # to update this task's progress
    
    await connection_manager.broadcast(update.task_id, update.dict())
    return update


@router.get("/status/{task_id}", response_model=ProgressUpdate)
async def get_progress(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest progress update for a specific task."""
    if task_id not in connection_manager.latest_updates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No progress updates found for task {task_id}"
        )
    
    return connection_manager.latest_updates[task_id]


@router.post("/create", response_model=ProgressUpdate)
async def create_progress_tracker(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new progress tracker and return its ID."""
    task_id = str(uuid4())
    progress_update = ProgressUpdate(
        task_id=task_id,
        overall_progress=0.0,
        status="initializing",
        message="Initializing task"
    )
    
    connection_manager.latest_updates[task_id] = progress_update
    return progress_update