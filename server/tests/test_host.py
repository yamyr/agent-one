import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.base_agent import BaseAgent
from app.host import Host
from app.narrator import Narrator


class _DummyAgent(BaseAgent):
    """Minimal agent for testing Host registration."""

    async def tick(self, host):
        pass


def _make_host():
    """Create a Host with a mocked narrator for testing."""
    narrator = MagicMock(spec=Narrator)
    narrator.feed = AsyncMock()
    narrator.reset = MagicMock()
    narrator.start = MagicMock()
    narrator.stop = MagicMock()
    return Host(narrator=narrator)


def _dummy(agent_id="rover-mock"):
    return _DummyAgent(agent_id=agent_id, interval=0.1)


class TestHostInbox(unittest.TestCase):
    def test_register_creates_inbox(self):
        host = _make_host()
        host.register(_dummy("rover-mock"))
        self.assertIn("rover-mock", host._inboxes)

    def test_send_and_drain(self):
        host = _make_host()
        host.register(_dummy("rover-mock"))
        host.send_command("rover-mock", {"name": "recall", "payload": {}})
        host.send_command("rover-mock", {"name": "assign_mission", "payload": {"objective": "Go"}})
        commands = host.drain_inbox("rover-mock")
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]["name"], "recall")
        self.assertEqual(commands[1]["name"], "assign_mission")

    def test_drain_empty_inbox(self):
        host = _make_host()
        host.register(_dummy("rover-mock"))
        commands = host.drain_inbox("rover-mock")
        self.assertEqual(commands, [])

    def test_drain_clears_inbox(self):
        host = _make_host()
        host.register(_dummy("rover-mock"))
        host.send_command("rover-mock", {"name": "recall", "payload": {}})
        host.drain_inbox("rover-mock")
        commands = host.drain_inbox("rover-mock")
        self.assertEqual(commands, [])

    def test_send_to_unknown_agent(self):
        host = _make_host()
        # Should not raise, just log warning
        host.send_command("nonexistent", {"name": "recall", "payload": {}})

    def test_drain_unknown_agent(self):
        host = _make_host()
        commands = host.drain_inbox("nonexistent")
        self.assertEqual(commands, [])


class TestHostBroadcast(unittest.TestCase):
    def test_broadcast_sends_and_feeds_narrator(self):
        host = _make_host()
        msg = {"type": "event", "name": "test"}

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            asyncio.run(host.broadcast(msg))
            mock_bc.send.assert_called_once_with(msg)

        host._narrator.feed.assert_called_once_with(msg)


class TestHostStationRouting(unittest.TestCase):
    def test_route_station_actions_assign_mission(self):
        host = _make_host()
        host.register(_dummy("rover-mock"))

        result = {
            "thinking": "Assigning mission.",
            "actions": [
                {
                    "name": "assign_mission",
                    "params": {"agent_id": "rover-mock", "objective": "Go north"},
                },
            ],
        }

        with patch("app.host.station_execute_action") as mock_exec:
            mock_exec.return_value = {"ok": True, "agent_id": "rover-mock", "objective": "Go north"}
            with patch("app.host.broadcaster") as mock_bc:
                mock_bc.send = AsyncMock()
                asyncio.run(host.route_station_actions(result))

        # Command should be in rover inbox
        commands = host.drain_inbox("rover-mock")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["name"], "assign_mission")
        self.assertEqual(commands[0]["payload"]["objective"], "Go north")

    def test_route_station_actions_broadcast_alert(self):
        host = _make_host()

        result = {
            "thinking": None,
            "actions": [
                {"name": "broadcast_alert", "params": {"message": "Storm!"}},
            ],
        }

        with patch("app.host.station_execute_action") as mock_exec:
            mock_exec.return_value = {"ok": True, "message": "Storm!"}
            with patch("app.host.broadcaster") as mock_bc:
                mock_bc.send = AsyncMock()
                asyncio.run(host.route_station_actions(result))
                # Verify broadcast was called
                mock_bc.send.assert_called()


class TestHostAbortMission(unittest.TestCase):
    def setUp(self):
        from app.world import world

        self._original_status = world.get_mission()["status"]

    def tearDown(self):
        from app.world import world

        world.get_mission()["status"] = self._original_status

    def test_abort_broadcasts_event(self):
        from app.world import world

        world.get_mission()["status"] = "running"
        host = _make_host()

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            result = asyncio.run(host.abort_mission("test abort"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "aborted")
        self.assertEqual(result["reason"], "test abort")
        host._narrator.feed.assert_called_once()

    def test_abort_already_ended(self):
        from app.world import world

        world.get_mission()["status"] = "success"
        host = _make_host()

        result = asyncio.run(host.abort_mission("too late"))
        self.assertFalse(result["ok"])
        self.assertIn("already ended", result["error"])


class TestHostRecall(unittest.TestCase):
    def test_recall_enqueues_command(self):
        host = _make_host()
        host.register(_dummy("rover-mock"))

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            result = asyncio.run(host.recall_rover("rover-mock"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["rover_id"], "rover-mock")

        commands = host.drain_inbox("rover-mock")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["name"], "recall")

    def test_recall_unknown_rover(self):
        host = _make_host()

        result = asyncio.run(host.recall_rover("nonexistent"))

        self.assertFalse(result["ok"])
        self.assertIn("Unknown rover", result["error"])

class TestHostStationLoop(unittest.TestCase):
    def _make_host(self):
        narrator = unittest.mock.MagicMock()
        narrator.feed = unittest.mock.AsyncMock()
        return Host(narrator)

    def test_register_station_loop(self):
        from app.agent import StationLoop
        host = self._make_host()
        loop = StationLoop.__new__(StationLoop)
        loop.agent_id = "station-loop"
        host.register(loop)
        self.assertIs(host._station_loop, loop)

    def test_register_non_station_loop(self):
        host = self._make_host()
        agent = unittest.mock.MagicMock()
        agent.agent_id = "rover-mistral"
        agent.__class__ = type("Other", (), {})
        host.register(agent)
        self.assertIsNone(host._station_loop)

    def test_broadcast_feeds_interesting_events(self):
        from app.agent import StationLoop
        host = self._make_host()
        loop = StationLoop.__new__(StationLoop)
        loop.agent_id = "station-loop"
        loop._event_buffer = []
        loop.buffer_event = unittest.mock.MagicMock()
        host._station_loop = loop
        msg = {"source": "rover-mistral", "name": "dig", "payload": {}}
        import asyncio
        asyncio.run(host.broadcast(msg))
        loop.buffer_event.assert_called_once_with(msg)

    def test_broadcast_ignores_station_events(self):
        from app.agent import StationLoop
        host = self._make_host()
        loop = StationLoop.__new__(StationLoop)
        loop.agent_id = "station-loop"
        loop.buffer_event = unittest.mock.MagicMock()
        host._station_loop = loop
        msg = {"source": "station", "name": "thinking", "payload": {}}
        import asyncio
        asyncio.run(host.broadcast(msg))
        loop.buffer_event.assert_not_called()

    def test_broadcast_ignores_uninteresting_events(self):
        from app.agent import StationLoop
        host = self._make_host()
        loop = StationLoop.__new__(StationLoop)
        loop.agent_id = "station-loop"
        loop.buffer_event = unittest.mock.MagicMock()
        host._station_loop = loop
        msg = {"source": "rover-mistral", "name": "move", "payload": {}}
        import asyncio
        asyncio.run(host.broadcast(msg))
        loop.buffer_event.assert_not_called()

    def test_stop_clears_station_loop(self):
        host = self._make_host()
        host._station_loop = "something"
        host.stop()
        self.assertIsNone(host._station_loop)


class TestStationLoopUnit(unittest.TestCase):
    def test_buffer_event(self):
        from app.agent import StationLoop
        loop = StationLoop.__new__(StationLoop)
        loop._event_buffer = []
        loop.buffer_event({"name": "dig", "source": "rover"})
        self.assertEqual(len(loop._event_buffer), 1)

    def test_buffer_caps_at_50(self):
        from app.agent import StationLoop
        loop = StationLoop.__new__(StationLoop)
        loop._event_buffer = [{"n": i} for i in range(50)]
        loop.buffer_event({"n": 50})
        self.assertEqual(len(loop._event_buffer), 50)
        self.assertEqual(loop._event_buffer[-1]["n"], 50)
        self.assertEqual(loop._event_buffer[0]["n"], 1)

    def test_tick_skips_when_buffer_empty(self):
        from app.agent import StationLoop
        loop = StationLoop.__new__(StationLoop)
        loop._event_buffer = []
        host = unittest.mock.MagicMock()
        import asyncio
        asyncio.run(loop.tick(host))
        host.broadcast.assert_not_called()

    def test_tick_calls_evaluate_and_clears_buffer(self):
        from app.agent import StationLoop
        loop = StationLoop.__new__(StationLoop)
        loop._event_buffer = [{"name": "scan", "source": "drone", "payload": {}}]
        loop._station = unittest.mock.MagicMock()
        loop._station.evaluate_situation.return_value = {"thinking": "", "actions": []}
        mock_world = unittest.mock.MagicMock()
        mock_world.observe_station.return_value = unittest.mock.MagicMock()
        loop._world = mock_world
        host = unittest.mock.AsyncMock()
        import asyncio
        asyncio.run(loop.tick(host))
        self.assertEqual(len(loop._event_buffer), 0)

    def test_interesting_events_frozenset(self):
        from app.agent import StationLoop
        self.assertIsInstance(StationLoop.INTERESTING_EVENTS, frozenset)
        self.assertIn("dig", StationLoop.INTERESTING_EVENTS)
        self.assertIn("scan", StationLoop.INTERESTING_EVENTS)
        self.assertNotIn("move", StationLoop.INTERESTING_EVENTS)

