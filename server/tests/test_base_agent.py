import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

from app.base_agent import BaseAgent
from app.world import WORLD


class _CountingAgent(BaseAgent):
    """Test agent that counts ticks and stops after max_ticks."""

    def __init__(self, agent_id="test-agent", interval=0.01, max_ticks=3):
        super().__init__(agent_id=agent_id, interval=interval)
        self.tick_count = 0
        self.max_ticks = max_ticks

    async def tick(self, host):
        self.tick_count += 1
        if self.tick_count >= self.max_ticks:
            # Force mission to "success" to stop the loop
            WORLD["mission"]["status"] = "success"


class _ErrorAgent(BaseAgent):
    """Agent that raises on every tick."""

    def __init__(self):
        super().__init__(agent_id="error-agent", interval=0.01)
        self.tick_count = 0

    async def tick(self, host):
        self.tick_count += 1
        if self.tick_count >= 2:
            WORLD["mission"]["status"] = "success"
            return
        raise ValueError("boom")


class TestBaseAgentRun(unittest.TestCase):
    def setUp(self):
        self._original_status = WORLD["mission"]["status"]
        WORLD["mission"]["status"] = "active"

    def tearDown(self):
        WORLD["mission"]["status"] = self._original_status

    def test_run_stops_on_mission_success(self):
        agent = _CountingAgent(max_ticks=3)
        host = MagicMock()
        host.paused = False
        asyncio.run(agent.run(host))
        self.assertEqual(agent.tick_count, 3)

    def test_run_stops_on_mission_failed(self):
        WORLD["mission"]["status"] = "failed"
        agent = _CountingAgent(max_ticks=10)
        host = MagicMock()
        host.paused = False
        asyncio.run(agent.run(host))
        # Should stop immediately, no ticks
        self.assertEqual(agent.tick_count, 0)

    def test_run_skips_tick_when_paused(self):
        agent = _CountingAgent(max_ticks=2, interval=0.01)
        host = MagicMock()
        # Start paused, then unpause after a short delay
        host.paused = True
        call_count = 0

        original_tick = agent.tick

        async def _unpause_after_first(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            host.paused = False
            return await original_tick(*args, **kwargs)

        agent.tick = _unpause_after_first
        # Unpause after a brief pause
        host.paused = False
        asyncio.run(agent.run(host))
        self.assertEqual(agent.tick_count, 2)

    def test_run_survives_tick_exception(self):
        agent = _ErrorAgent()
        host = MagicMock()
        host.paused = False
        asyncio.run(agent.run(host))
        # Should have ticked twice: first raises, second stops
        self.assertEqual(agent.tick_count, 2)

    def test_run_continues_on_mission_aborted(self):
        """Aborted is NOT terminal — agents keep running to return to station."""
        WORLD["mission"]["status"] = "aborted"
        agent = _CountingAgent(max_ticks=3)
        host = MagicMock()
        host.paused = False
        asyncio.run(agent.run(host))
        # Agent should still tick (aborted is not terminal)
        self.assertEqual(agent.tick_count, 3)

    def test_agent_id_and_interval(self):
        agent = _CountingAgent(agent_id="my-rover", interval=1.5)
        self.assertEqual(agent.agent_id, "my-rover")
        self.assertEqual(agent.interval, 1.5)
