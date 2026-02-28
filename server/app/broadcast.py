"""WebSocket broadcast manager for streaming simulation events to all connected clients."""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class Broadcaster:
    """Manages WebSocket connections and broadcasts events to all clients."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"Client connected ({len(self._connections)} total)")

    def disconnect(self, ws: WebSocket):
        self._connections.remove(ws)
        logger.info(f"Client disconnected ({len(self._connections)} total)")

    async def send(self, event: dict):
        """Broadcast an event dict to all connected clients."""
        data = json.dumps(event)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


broadcaster = Broadcaster()
