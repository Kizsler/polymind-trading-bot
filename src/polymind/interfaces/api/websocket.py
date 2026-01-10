"""WebSocket connection manager for real-time updates."""

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from polymind.utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("WebSocket client connected. Total: {}", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: {}", len(self._connections))

    async def broadcast(self, event_type: str, data: Any) -> None:
        """Broadcast a message to all connected clients.

        Args:
            event_type: Type of event (trade, status, settings, wallet)
            data: Event data to send
        """
        if not self._connections:
            return

        message = json.dumps({"type": event_type, "data": data})

        # Send to all connections, removing dead ones
        dead_connections = []

        async with self._lock:
            for connection in self._connections:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_text(message)
                except Exception as e:
                    logger.warning("Failed to send to WebSocket: {}", str(e))
                    dead_connections.append(connection)

            # Clean up dead connections
            for dead in dead_connections:
                if dead in self._connections:
                    self._connections.remove(dead)

        if dead_connections:
            logger.info("Removed {} dead connections", len(dead_connections))

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)


# Global connection manager instance
manager = ConnectionManager()
