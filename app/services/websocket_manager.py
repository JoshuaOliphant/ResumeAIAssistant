from __future__ import annotations

import time
import logging
import traceback
from typing import Dict, Set, Optional, List

import logfire
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Global websocket manager instance
_websocket_manager: Optional[WebSocketManager] = None

async def get_websocket_manager() -> WebSocketManager:
    """
    Get or create the global WebSocketManager instance.
    
    This is a singleton factory function that returns the global WebSocketManager instance.
    If the instance doesn't exist yet, it creates one.
    
    Returns:
        WebSocketManager: The global WebSocketManager instance
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
        logfire.info("Created global WebSocketManager instance")
    return _websocket_manager


class WebSocketManager:
    """Track WebSocket connections for progress updates."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Track connection metrics
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "closed_connections": 0,
            "error_connections": 0,
        }
        # Track client info for debugging
        self.client_info: Dict[WebSocket, Dict] = {}

    async def register(self, customization_id: str, websocket: WebSocket) -> None:
        """Register a new connection for a customization."""
        # Log connection details before accepting
        client_host = None
        client_port = None
        headers = {}
        
        try:
            # Extract client information
            client_host = websocket.client.host if hasattr(websocket, 'client') and websocket.client else None
            client_port = websocket.client.port if hasattr(websocket, 'client') and websocket.client else None
            
            # Extract headers safely
            if hasattr(websocket, 'headers'):
                headers = {k: v for k, v in websocket.headers.items() 
                           if k.lower() not in ('authorization', 'cookie')}
                
            # Log connection attempt
            logfire.info(
                "WebSocket connection attempt",
                customization_id=customization_id,
                client_host=client_host,
                client_port=client_port,
                headers_count=len(headers),
                timestamp=time.time(),
            )
            
            # Accept the connection
            await websocket.accept()
            
            # Store client info for debugging
            self.client_info[websocket] = {
                "customization_id": customization_id,
                "client_host": client_host,
                "client_port": client_port,
                "connected_at": time.time(),
                "messages_sent": 0,
                "last_message_at": None,
            }
            
            # Register the connection
            self.active_connections.setdefault(customization_id, set()).add(websocket)
            
            # Update stats
            self.connection_stats["total_connections"] += 1
            self.connection_stats["active_connections"] += 1
            
            # Log successful connection
            logfire.info(
                "WebSocket registered successfully", 
                customization_id=customization_id,
                client_host=client_host,
                client_port=client_port,
                active_connections=self.connection_stats["active_connections"],
                total_connections=self.connection_stats["total_connections"],
            )
            
        except Exception as e:
            # Log connection error
            self.connection_stats["error_connections"] += 1
            logfire.error(
                "Error registering WebSocket connection",
                customization_id=customization_id,
                client_host=client_host,
                client_port=client_port,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exception(type(e), e, e.__traceback__),
            )
            raise

    def remove(self, customization_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        try:
            # Get client info for logging
            client_info = self.client_info.get(websocket, {})
            client_host = client_info.get("client_host")
            client_port = client_info.get("client_port")
            connected_at = client_info.get("connected_at")
            
            # Calculate connection duration if we have the connection time
            connection_duration = None
            if connected_at:
                connection_duration = time.time() - connected_at
            
            # Remove from active connections
            connections = self.active_connections.get(customization_id)
            removed = False
            if connections and websocket in connections:
                connections.remove(websocket)
                removed = True
                if not connections:
                    self.active_connections.pop(customization_id, None)
            
            # Update stats if removed
            if removed:
                self.connection_stats["active_connections"] = max(0, self.connection_stats["active_connections"] - 1)
                self.connection_stats["closed_connections"] += 1
            
            # Clean up client info
            if websocket in self.client_info:
                del self.client_info[websocket]
            
            # Log removal with detailed info
            logfire.info(
                "WebSocket connection removed",
                customization_id=customization_id,
                client_host=client_host,
                client_port=client_port,
                connection_duration=connection_duration,
                messages_sent=client_info.get("messages_sent", 0),
                removed_from_active=removed,
                remaining_active=self.connection_stats["active_connections"],
            )
        except Exception as e:
            # Log error during removal but don't re-raise
            logfire.error(
                "Error removing WebSocket connection",
                customization_id=customization_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )

    async def send_json(self, customization_id: str, message: dict) -> None:
        """Send a JSON message to all connections for a customization."""
        # Track message delivery stats
        send_stats = {
            "total_attempts": 0,
            "success": 0,
            "disconnect_error": 0,
            "other_error": 0,
        }
        
        # Get all active connections for this customization
        connections = list(self.active_connections.get(customization_id, set()))
        
        # Log message sending attempt
        logfire.info(
            "Sending WebSocket message",
            customization_id=customization_id,
            message_type=message.get("type", "unknown"),
            connections_count=len(connections),
            message_keys=list(message.keys()),
        )
        
        # Track message delivery status for each connection
        for connection in connections:
            send_stats["total_attempts"] += 1
            client_info = self.client_info.get(connection, {})
            
            try:
                # Send the message
                await connection.send_json(message)
                send_stats["success"] += 1
                
                # Update client info stats
                if connection in self.client_info:
                    self.client_info[connection]["messages_sent"] += 1
                    self.client_info[connection]["last_message_at"] = time.time()
                
            except WebSocketDisconnect:
                # Handle normal disconnection
                send_stats["disconnect_error"] += 1
                logfire.info(
                    "WebSocket disconnected during send",
                    customization_id=customization_id,
                    client_host=client_info.get("client_host"),
                    client_port=client_info.get("client_port"),
                )
                self.remove(customization_id, connection)
                
            except Exception as exc:
                # Handle other errors
                send_stats["other_error"] += 1
                logfire.warning(
                    "Failed to send WebSocket message",
                    customization_id=customization_id,
                    client_host=client_info.get("client_host"),
                    client_port=client_info.get("client_port"),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    traceback=traceback.format_exception(type(exc), exc, exc.__traceback__),
                )
                self.remove(customization_id, connection)
        
        # Log summary of send operation
        logfire.info(
            "WebSocket message send complete",
            customization_id=customization_id,
            success_count=send_stats["success"],
            disconnect_count=send_stats["disconnect_error"],
            error_count=send_stats["other_error"],
            total_attempts=send_stats["total_attempts"],
        )
