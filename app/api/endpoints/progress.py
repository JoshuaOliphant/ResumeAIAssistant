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

from app.core.security import get_current_user, get_token_from_cookie
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
            return
        
        connections = self.active_connections[user_id]
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except RuntimeError:
                # Connection already closed
                disconnected.append(websocket)
        
        # Clean up any disconnected sockets
        for websocket in disconnected:
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
        return get_current_user(token=token, db=db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    task_id: str, 
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for receiving real-time progress updates."""
    user = await get_user_from_token(websocket, db)
    if not user:
        return
    
    user_id = str(user.id)
    await connection_manager.connect(websocket, user_id)
    connection_manager.subscribe(task_id, user_id)
    
    try:
        while True:
            # Wait for messages - these could be used for bidirectional communication
            # like subscribing to different tasks or requesting status updates
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if "type" in message:
                    if message["type"] == "subscribe" and "task_id" in message:
                        connection_manager.subscribe(message["task_id"], user_id)
                    elif message["type"] == "unsubscribe" and "task_id" in message:
                        connection_manager.unsubscribe(message["task_id"], user_id)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
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