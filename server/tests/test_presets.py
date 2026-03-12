"""Tests for multi-scenario simulation presets."""

import copy

import pytest

from app.presets import PRESETS, apply_preset, list_presets, _agent_matches_pattern
from app.world import WORLD, reset_world
from app.config import settings


@pytest.fixture(autouse=True)
def _fresh_world():
    """Reset WORLD state before and after each test."""
    reset_world()
    yield
    reset_world()


# ── T001: Preset definitions ───────────────────────────────────────────────


class TestPresetDefinitions:
    """T001: Verify all presets exist with required fields."""

    REQUIRED_KEYS = {"name", "description", "world_overrides", "agent_overrides"}
    EXPECTED_PRESETS = {
        "default",
        "storm_survival",
        "resource_race",
        "exploration",
        "cooperative",
        "demo_timeline",
    }

    def test_all_expected_presets_exist(self):
        assert set(PRESETS.keys()) == self.EXPECTED_PRESETS

    def test_each_preset_has_required_keys(self):
        for name, preset in PRESETS.items():
            missing = self.REQUIRED_KEYS - set(preset.keys())
            assert not missing, f"Preset {name!r} missing keys: {missing}"

    def test_each_preset_has_name_matching_key(self):
        for key, preset in PRESETS.items():
            assert preset["name"] == key

    def test_each_preset_has_nonempty_description(self):
        for name, preset in PRESETS.items():
            assert isinstance(preset["description"], str)
            assert len(preset["description"]) > 10, f"Preset {name!r} description too short"

    def test_world_overrides_is_dict(self):
        for name, preset in PRESETS.items():
            assert isinstance(preset["world_overrides"], dict), f"Preset {name!r}"

    def test_agent_overrides_is_dict(self):
        for name, preset in PRESETS.items():
            assert isinstance(preset["agent_overrides"], dict), f"Preset {name!r}"


# ── T002: Default preset ───────────────────────────────────────────────────


class TestDefaultPreset:
    """T002: Default preset applies no changes."""

    def test_default_preset_no_world_overrides(self):
        assert PRESETS["default"]["world_overrides"] == {}

    def test_default_preset_no_agent_overrides(self):
        assert PRESETS["default"]["agent_overrides"] == {}

    def test_default_preset_no_active_agents_override(self):
        assert PRESETS["default"]["active_agents"] is None

    def test_apply_default_preserves_world(self):
        before = copy.deepcopy(WORLD)
        apply_preset("default", WORLD)
        # Key world state should be unchanged
        assert WORLD["storm"] == before["storm"]
        assert WORLD["mission"] == before["mission"]
        for agent_id in before["agents"]:
            assert WORLD["agents"][agent_id]["battery"] == before["agents"][agent_id]["battery"]


# ── T003: Storm survival preset ────────────────────────────────────────────


class TestStormSurvivalPreset:
    """T003: Storm survival modifies world and agent state."""

    def test_storm_next_tick_set_early(self):
        apply_preset("storm_survival", WORLD)
        assert WORLD["storm"]["next_storm_tick"] == 5

    def test_rover_battery_reduced(self):
        apply_preset("storm_survival", WORLD)
        assert WORLD["agents"]["rover-mistral"]["battery"] == 0.5

    def test_hauler_battery_reduced(self):
        apply_preset("storm_survival", WORLD)
        assert WORLD["agents"]["hauler-mistral"]["battery"] == 0.6

    def test_drone_battery_reduced(self):
        apply_preset("storm_survival", WORLD)
        assert WORLD["agents"]["drone-mistral"]["battery"] == 0.5

    def test_active_agents_specified(self):
        preset = PRESETS["storm_survival"]
        assert preset["active_agents"] is not None
        agents = [a.strip() for a in preset["active_agents"].split(",")]
        assert "rover-mistral" in agents
        assert "station-loop" in agents


# ── T004: Unknown preset ───────────────────────────────────────────────────


class TestUnknownPreset:
    """T004: Unknown preset raises ValueError."""

    def test_apply_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            apply_preset("nonexistent", WORLD)

    def test_apply_empty_string_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            apply_preset("", WORLD)


# ── T005: Resource race preset ─────────────────────────────────────────────


class TestResourceRacePreset:
    """Verify resource_race preset overrides."""

    def test_target_quantity_reduced(self):
        apply_preset("resource_race", WORLD)
        assert WORLD["mission"]["target_quantity"] == 150

    def test_all_rovers_full_battery(self):
        apply_preset("resource_race", WORLD)
        for agent_id, state in WORLD["agents"].items():
            if "rover" in agent_id:
                assert state["battery"] == 1.0

    def test_multiple_rovers_in_active_agents(self):
        preset = PRESETS["resource_race"]
        agents = [a.strip() for a in preset["active_agents"].split(",")]
        rover_count = sum(1 for a in agents if "rover" in a)
        assert rover_count >= 3


# ── T006: Exploration preset ──────────────────────────────────────────────


class TestExplorationPreset:
    """Verify exploration preset overrides."""

    def test_high_target_quantity(self):
        apply_preset("exploration", WORLD)
        assert WORLD["mission"]["target_quantity"] == 600

    def test_rover_battery_moderate(self):
        apply_preset("exploration", WORLD)
        assert WORLD["agents"]["rover-mistral"]["battery"] == 0.8

    def test_drone_full_battery(self):
        apply_preset("exploration", WORLD)
        assert WORLD["agents"]["drone-mistral"]["battery"] == 1.0


# ── T007: Cooperative preset ─────────────────────────────────────────────


class TestCooperativePreset:
    """Verify cooperative preset overrides."""

    def test_target_quantity_high(self):
        apply_preset("cooperative", WORLD)
        assert WORLD["mission"]["target_quantity"] == 500

    def test_multiple_rovers_active(self):
        preset = PRESETS["cooperative"]
        agents = [a.strip() for a in preset["active_agents"].split(",")]
        rover_count = sum(1 for a in agents if "rover" in a)
        assert rover_count >= 3


# ── Agent pattern matching ─────────────────────────────────────────────────


class TestAgentPatternMatching:
    """Verify wildcard pattern matching for agent overrides."""

    def test_exact_match(self):
        assert _agent_matches_pattern("rover-mistral", "rover-mistral") is True

    def test_exact_no_match(self):
        assert _agent_matches_pattern("rover-mistral", "rover-2") is False

    def test_wildcard_both_sides(self):
        assert _agent_matches_pattern("rover-mistral", "*rover*") is True
        assert _agent_matches_pattern("rover-2", "*rover*") is True
        assert _agent_matches_pattern("drone-mistral", "*rover*") is False

    def test_wildcard_drone(self):
        assert _agent_matches_pattern("drone-mistral", "*drone*") is True
        assert _agent_matches_pattern("rover-mistral", "*drone*") is False

    def test_wildcard_hauler(self):
        assert _agent_matches_pattern("hauler-mistral", "*hauler*") is True


# ── list_presets ───────────────────────────────────────────────────────────


class TestListPresets:
    """Verify list_presets returns correct summaries."""

    def test_returns_all_presets(self):
        result = list_presets()
        assert len(result) == len(PRESETS)

    def test_each_entry_has_name_and_description(self):
        for entry in list_presets():
            assert "name" in entry
            assert "description" in entry

    def test_no_extra_keys(self):
        for entry in list_presets():
            assert set(entry.keys()) == {"name", "description"}


# ── T010: Config preset field ──────────────────────────────────────────────


class TestConfigPresetField:
    """T010: Verify Settings has preset field."""

    def test_preset_field_exists(self):
        assert hasattr(settings, "preset")

    def test_preset_default_value(self):
        assert settings.preset == "default"

    def test_preset_is_string(self):
        assert isinstance(settings.preset, str)
