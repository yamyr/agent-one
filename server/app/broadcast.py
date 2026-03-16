"""WebSocket broadcast manager for streaming simulation events to all connected clients."""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_WS_CONNECTIONS = 50


class Broadcaster:
    """Manages WebSocket connections and broadcasts events to all clients."""

    def __init__(self):
        # Use a set for O(1) add/remove (avoids O(n) list.remove on disconnect)
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        if len(self._connections) >= MAX_WS_CONNECTIONS:
            await ws.close(code=1013, reason="Too many connections")
            logger.warning("Rejected WebSocket: connection limit (%d) reached", MAX_WS_CONNECTIONS)
            return
        await ws.accept()
        self._connections.add(ws)
        logger.info("Client connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)
        logger.info("Client disconnected (%d total)", len(self._connections))

    async def send(self, event: dict):
        """Broadcast an event dict to all connected clients."""
        data = json.dumps(event)
        dead: set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
                logger.warning("Removing dead WebSocket connection")
        self._connections -= dead


broadcaster = Broadcaster()
