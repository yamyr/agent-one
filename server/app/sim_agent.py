"""MockSimAgent: wraps SimulationEngine and picks random legal actions each turn."""
from __future__ import annotations

import dataclasses
import random

from .sim import SimulationEngine, WorldFactory


def _serialize(obj: object) -> object:
    """Recursively convert dataclasses, tuples, and sets to JSON-safe types."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, set):
        return [_serialize(v) for v in sorted(obj)]
    return obj


class MockSimAgent:
    """Deterministic random agent for demo purposes."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        factory = WorldFactory(width=12, height=12, target_count=2)
        world = factory.create(seed=seed)
        self.engine = SimulationEngine(world, step_limit=400)

    # -- public API ----------------------------------------------------------

    def run_turn(self) -> tuple[dict, dict]:
        """Pick a random legal action, execute it, return (step_result, observation)."""
        actions = self.engine.get_legal_actions()
        if not actions:
            return self._terminal_result(), self.get_observation()

        action = self._rng.choice(actions)
        result = self.engine.step(action)
        return self._step_to_dict(result), self.get_observation()

    def get_observation(self) -> dict:
        obs = self.engine.get_observation("rover")
        return _serialize(obs)

    def is_terminal(self) -> bool:
        return self.engine.is_terminal()

    # -- internals -----------------------------------------------------------

    def _step_to_dict(self, result) -> dict:
        return {
            "tick": result.tick,
            "accepted": result.accepted,
            "action": _serialize(result.action),
            "events": [_serialize(e) for e in result.events],
            "terminal_status": result.terminal_status,
        }

    def _terminal_result(self) -> dict:
        obs = self.engine.get_observation("rover")
        return {
            "tick": obs.tick,
            "accepted": False,
            "action": {"kind": "wait"},
            "events": [{"name": "terminal_world", "payload": {}}],
            "terminal_status": obs.status,
        }
