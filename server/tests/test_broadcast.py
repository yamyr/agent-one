"""Tests for Broadcaster safety guards."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.broadcast import Broadcaster


class TestBroadcasterDisconnect(unittest.TestCase):
    """Verify disconnect() handles edge cases safely."""

    def test_disconnect_removes_connection(self):
        b = Broadcaster()
        ws = MagicMock()
        b._connections.add(ws)
        b.disconnect(ws)
        self.assertNotIn(ws, b._connections)

    def test_double_disconnect_no_error(self):
        """Double-disconnect must not raise ValueError."""
        b = Broadcaster()
        ws = MagicMock()
        b._connections.add(ws)
        b.disconnect(ws)
        b.disconnect(ws)  # should not raise
        self.assertEqual(len(b._connections), 0)

    def test_disconnect_unknown_ws_no_error(self):
        """Disconnecting a never-connected ws must not raise."""
        b = Broadcaster()
        ws = MagicMock()
        b.disconnect(ws)  # should not raise


class TestBroadcasterSend(unittest.TestCase):
    """Verify send() handles dead connections and mutation safety."""

    def test_send_to_healthy_connections(self):
        b = Broadcaster()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        b._connections = {ws1, ws2}
        asyncio.run(b.send({"type": "test"}))
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    def test_send_removes_dead_connections(self):
        b = Broadcaster()
        healthy = AsyncMock()
        dead = AsyncMock()
        dead.send_text.side_effect = ConnectionError("gone")
        b._connections = {healthy, dead}
        asyncio.run(b.send({"type": "test"}))
        self.assertIn(healthy, b._connections)
        self.assertNotIn(dead, b._connections)

    def test_send_iterates_copy(self):
        """Mutation during iteration must not raise."""
        b = Broadcaster()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text.side_effect = RuntimeError("drop")
        b._connections = {ws1, ws2}
        # Should not raise ConcurrentModificationError
        asyncio.run(b.send({"type": "test"}))
        self.assertEqual(len(b._connections), 1)
