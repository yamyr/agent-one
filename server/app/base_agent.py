"""BaseAgent — abstract base class for self-running agents.

Agents own their run loop. The Host provides inbox, broadcast, and lifecycle only.
Subclasses implement tick() with their observe/reason/act cycle.
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from .world import World, world as default_world

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Self-running agent. Owns the loop, Host is just a router."""

    def __init__(self, agent_id: str, interval: float, world: World | None = None):
        self.agent_id = agent_id
        self.interval = interval
        self._world = world or default_world

    @abstractmethod
    async def tick(self, host) -> None:
        """One observe/reason/act cycle. Subclasses implement this."""

    async def run(self, host) -> None:
        """Self-running loop. Checks mission status and pause state."""
        while True:
            mission_status = self._world.get_mission()["status"]
            if mission_status in ("success", "failed"):
                logger.info("Agent loop stopped (%s): mission %s", self.agent_id, mission_status)
                return

            if host.paused:
                await asyncio.sleep(self.interval)
                continue

            try:
                await self.tick(host)
            except Exception:
                logger.exception("Agent tick error (%s)", self.agent_id)

            await asyncio.sleep(self.interval)
