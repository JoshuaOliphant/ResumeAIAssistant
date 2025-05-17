from __future__ import annotations

import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Track WebSocket connections for progress updates."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def register(self, customization_id: str, websocket: WebSocket) -> None:
        """Register a new connection for a customization."""
        await websocket.accept()
        self.active_connections.setdefault(customization_id, set()).add(websocket)
        logger.debug("WebSocket registered", extra={"customization_id": customization_id})

    def remove(self, customization_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        connections = self.active_connections.get(customization_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self.active_connections.pop(customization_id, None)
        logger.debug("WebSocket removed", extra={"customization_id": customization_id})

    async def send_json(self, customization_id: str, message: dict) -> None:
        """Send a JSON message to all connections for a customization."""
        connections = list(self.active_connections.get(customization_id, set()))
        for connection in connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.remove(customization_id, connection)
            except Exception as exc:  # pragma: no cover - log unexpected errors
                logger.warning("Failed to send WebSocket message", extra={"error": str(exc)})
                self.remove(customization_id, connection)
