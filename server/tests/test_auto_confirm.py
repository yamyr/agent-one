"""Tests for automatic hazard-detection confirmation system.

Covers: detect_move_hazards() in world.py, _auto_confirm_gate() in agent.py,
config toggle, and edge cases.
"""

import asyncio

from app.world import (
    world,
    detect_move_hazards,
    BATTERY_THRESHOLD_AUTO_CONFIRM,
)
from app.agent import _auto_confirm_gate
from app.config import settings


# ── Helpers ──


def _setup_agent(agent_id="rover-mistral", position=None, battery=1.0):
    """Set up a test agent with specified position and battery."""
    agent = world.state["agents"].get(agent_id)
    if agent is not None:
        if position is not None:
            agent["position"] = list(position)
        agent["battery"] = battery
    return agent


def _place_geyser(position, state="idle"):
    """Place a geyser obstacle at the given position with the given state."""
    obs = {"position": list(position), "kind": "geyser", "state": state, "_cycle_tick": 0}
    world.state.setdefault("obstacles", []).append(obs)
    # Update spatial index
    from app.world import _obstacle_index

    _obstacle_index[tuple(position)] = obs
    return obs


def _set_storm(phase="clear", intensity=0.0):
    """Set the storm state in the world."""
    storm = world.state.setdefault("storm", {})
    storm["phase"] = phase
    storm["intensity"] = intensity
    storm["next_storm_tick"] = 9999
    storm["active_start"] = 0
    storm["active_end"] = 9999
    storm["warning_start"] = 0


def _cleanup_geysers():
    """Remove all geysers from obstacles and index."""
    from app.world import _obstacle_index

    obstacles = world.state.get("obstacles", [])
    world.state["obstacles"] = [o for o in obstacles if o.get("kind") != "geyser"]
    # Rebuild index by removing geyser entries
    keys_to_remove = [k for k, v in _obstacle_index.items() if v.get("kind") == "geyser"]
    for k in keys_to_remove:
        del _obstacle_index[k]


# ── Foundational Tests ──


class TestDetectMoveHazards:
    """Tests for detect_move_hazards() function."""

    def setup_method(self):
        """Reset world state before each test."""
        _cleanup_geysers()
        _set_storm("clear", 0.0)
        _setup_agent("rover-mistral", position=[5, 5], battery=1.0)

    def test_no_hazards_returns_empty_list(self):
        """No obstacles, full battery, no storm -> empty hazard list."""
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        assert result == []

    def test_imports_work(self):
        """Verify all imports are accessible."""
        assert BATTERY_THRESHOLD_AUTO_CONFIRM == 0.15
        assert callable(detect_move_hazards)

    # ── US1: Geyser hazard detection ──

    def test_geyser_erupting_detected(self):
        """Erupting geyser at destination triggers hazard."""
        _place_geyser([6, 5], state="erupting")
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        assert len(result) >= 1
        assert any("erupting" in h.lower() or "geyser" in h.lower() for h in result)

    def test_geyser_warning_detected(self):
        """Warning-phase geyser at destination triggers hazard."""
        _place_geyser([6, 5], state="warning")
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        assert len(result) >= 1
        assert any("warning" in h.lower() or "geyser" in h.lower() for h in result)

    def test_geyser_idle_no_hazard(self):
        """Idle geyser at destination does NOT trigger hazard."""
        _place_geyser([6, 5], state="idle")
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        # Should not contain geyser hazards (idle is safe)
        geyser_hazards = [h for h in result if "geyser" in h.lower()]
        assert len(geyser_hazards) == 0

    def test_no_geyser_no_hazard(self):
        """No obstacles at destination -> no geyser hazard."""
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        geyser_hazards = [h for h in result if "geyser" in h.lower()]
        assert len(geyser_hazards) == 0

    # ── US2: Low battery detection ──

    def test_low_battery_detected(self):
        """Battery dropping below 15% after move triggers hazard."""
        _setup_agent("rover-mistral", position=[5, 5], battery=0.16)
        result = detect_move_hazards("rover-mistral", 6, 5, 0.02)
        assert len(result) >= 1
        assert any("battery" in h.lower() for h in result)

    def test_battery_ok_no_hazard(self):
        """Battery staying above 15% after move -> no battery hazard."""
        _setup_agent("rover-mistral", position=[5, 5], battery=0.50)
        result = detect_move_hazards("rover-mistral", 6, 5, 0.02)
        battery_hazards = [h for h in result if "battery" in h.lower()]
        assert len(battery_hazards) == 0

    # ── US3: Storm detection ──

    def test_storm_high_intensity_detected(self):
        """Active storm with intensity > 0.5 triggers hazard."""
        _set_storm("active", 0.7)
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        assert len(result) >= 1
        assert any("storm" in h.lower() for h in result)

    def test_storm_low_intensity_no_hazard(self):
        """Active storm with intensity <= 0.5 does NOT trigger hazard."""
        _set_storm("active", 0.3)
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        storm_hazards = [h for h in result if "storm" in h.lower()]
        assert len(storm_hazards) == 0

    def test_storm_clear_no_hazard(self):
        """Clear storm phase does NOT trigger hazard."""
        _set_storm("clear", 0.0)
        result = detect_move_hazards("rover-mistral", 6, 5, 0.01)
        storm_hazards = [h for h in result if "storm" in h.lower()]
        assert len(storm_hazards) == 0

    # ── US4: Config toggle ──

    def test_config_enabled_default(self):
        """auto_confirm_enabled defaults to True."""
        assert settings.auto_confirm_enabled is True

    # ── US5 / Edge Cases ──

    def test_combined_hazards_single_message(self):
        """Multiple hazards are all returned in a single list."""
        _setup_agent("rover-mistral", position=[5, 5], battery=0.16)
        _place_geyser([6, 5], state="erupting")
        _set_storm("active", 0.7)
        result = detect_move_hazards("rover-mistral", 6, 5, 0.02)
        # Should have at least 3 hazards: geyser + battery + storm
        assert len(result) >= 3
        assert any("geyser" in h.lower() or "erupting" in h.lower() for h in result)
        assert any("battery" in h.lower() for h in result)
        assert any("storm" in h.lower() for h in result)


# ── Auto-confirm gate tests ──


class TestAutoConfirmGate:
    """Tests for _auto_confirm_gate() async function."""

    def setup_method(self):
        _cleanup_geysers()
        _set_storm("clear", 0.0)
        _setup_agent("rover-mistral", position=[5, 5], battery=1.0)

    def test_config_disabled_skips_hazard_check(self, monkeypatch):
        """When auto_confirm_enabled is False, gate returns None even with hazards."""
        monkeypatch.setattr(settings, "auto_confirm_enabled", False)
        _place_geyser([6, 5], state="erupting")
        result = asyncio.run(
            _auto_confirm_gate(None, "rover-mistral", "move", {"direction": "east", "distance": 1})
        )
        assert result is None
        monkeypatch.setattr(settings, "auto_confirm_enabled", True)

    def test_non_move_action_not_gated(self):
        """Non-move actions (dig, analyze) are never gated."""
        _place_geyser([5, 5], state="erupting")
        result = asyncio.run(_auto_confirm_gate(None, "rover-mistral", "dig", {}))
        assert result is None

        result2 = asyncio.run(_auto_confirm_gate(None, "rover-mistral", "analyze", {}))
        assert result2 is None

    def test_geyser_not_at_destination_no_hazard(self):
        """Geyser at a different tile than destination should not trigger."""
        _place_geyser([10, 10], state="erupting")  # Far away from (6,5)
        result = asyncio.run(
            _auto_confirm_gate(None, "rover-mistral", "move", {"direction": "east", "distance": 1})
        )
        # No hazards at (6,5), so gate returns None (proceed)
        assert result is None
