"""Tests for station power allocation and budget monitoring."""

import pytest

from app.world import (
    WORLD,
    allocate_power,
    check_power_budgets,
    reset_world,
    STATION_POWER_CAPACITY,
    POWER_WARN_COOLDOWN,
)


@pytest.fixture(autouse=True)
def _fresh_world():
    """Reset WORLD state before and after each test."""
    reset_world()
    yield
    reset_world()


# ── T006: allocate_power tool tests ──────────────────────────────────────────


class TestAllocatePower:
    """T006: allocate_power tool tests."""

    def test_valid_allocation_sets_budget(self):
        result = allocate_power("rover-mistral", 0.3)
        assert result["ok"] is True
        assert result["agent_id"] == "rover-mistral"
        assert result["amount"] == 0.3
        assert result["previous"] is None
        assert WORLD["power_budgets"]["rover-mistral"] == 0.3

    def test_update_overwrites_previous(self):
        allocate_power("rover-mistral", 0.3)
        result = allocate_power("rover-mistral", 0.5)
        assert result["ok"] is True
        assert result["previous"] == 0.3
        assert result["amount"] == 0.5
        assert WORLD["power_budgets"]["rover-mistral"] == 0.5

    def test_invalid_agent_returns_error(self):
        result = allocate_power("nonexistent-agent", 0.3)
        assert result["ok"] is False
        assert "Unknown agent" in result["error"]

    def test_station_agent_returns_error(self):
        result = allocate_power("station", 0.3)
        assert result["ok"] is False
        assert "station" in result["error"].lower()

    def test_amount_clamped_above_one(self):
        result = allocate_power("rover-mistral", 1.5)
        assert result["ok"] is True
        assert result["amount"] == 1.0
        assert WORLD["power_budgets"]["rover-mistral"] == 1.0

    def test_amount_clamped_below_zero(self):
        result = allocate_power("rover-mistral", -0.5)
        assert result["ok"] is True
        assert result["amount"] == 0.0
        assert WORLD["power_budgets"]["rover-mistral"] == 0.0

    def test_boundary_zero(self):
        result = allocate_power("rover-mistral", 0.0)
        assert result["ok"] is True
        assert result["amount"] == 0.0

    def test_boundary_one(self):
        result = allocate_power("rover-mistral", 1.0)
        assert result["ok"] is True
        assert result["amount"] == 1.0

    def test_multiple_agents_independent(self):
        allocate_power("rover-mistral", 0.3)
        allocate_power("drone-mistral", 0.4)
        assert WORLD["power_budgets"]["rover-mistral"] == 0.3
        assert WORLD["power_budgets"]["drone-mistral"] == 0.4


# ── T011: PowerBudgetWarning event tests ─────────────────────────────────────


class TestPowerBudgetWarning:
    """T011: PowerBudgetWarning event tests."""

    def test_warning_emitted_when_battery_below_budget(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.3
        WORLD["agents"]["rover-mistral"]["battery"] = 0.2
        events = check_power_budgets(tick=10)
        warnings = [e for e in events if e["type"] == "power_budget_warning"]
        assert len(warnings) == 1
        assert warnings[0]["agent_id"] == "rover-mistral"
        assert warnings[0]["battery"] == 0.2
        assert warnings[0]["budget"] == 0.3
        assert warnings[0]["deficit"] > 0

    def test_no_warning_when_battery_meets_budget(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.3
        WORLD["agents"]["rover-mistral"]["battery"] = 0.5
        events = check_power_budgets(tick=10)
        warnings = [e for e in events if e["type"] == "power_budget_warning"]
        assert len(warnings) == 0

    def test_no_warning_when_battery_equals_budget(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.3
        WORLD["agents"]["rover-mistral"]["battery"] = 0.3
        events = check_power_budgets(tick=10)
        warnings = [e for e in events if e["type"] == "power_budget_warning"]
        assert len(warnings) == 0

    def test_debounce_suppresses_warning_within_cooldown(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.3
        WORLD["agents"]["rover-mistral"]["battery"] = 0.2
        events1 = check_power_budgets(tick=10)
        assert len([e for e in events1 if e["type"] == "power_budget_warning"]) == 1
        # Within cooldown -- no warning
        events2 = check_power_budgets(tick=11)
        assert len([e for e in events2 if e["type"] == "power_budget_warning"]) == 0
        events3 = check_power_budgets(tick=12)
        assert len([e for e in events3 if e["type"] == "power_budget_warning"]) == 0

    def test_warning_resumes_after_cooldown(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.3
        WORLD["agents"]["rover-mistral"]["battery"] = 0.2
        check_power_budgets(tick=10)
        # After cooldown
        events = check_power_budgets(tick=10 + POWER_WARN_COOLDOWN)
        warnings = [e for e in events if e["type"] == "power_budget_warning"]
        assert len(warnings) == 1

    def test_no_events_when_no_budgets_set(self):
        events = check_power_budgets(tick=10)
        assert len(events) == 0

    def test_deficit_value_correct(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.5
        WORLD["agents"]["rover-mistral"]["battery"] = 0.2
        events = check_power_budgets(tick=10)
        warnings = [e for e in events if e["type"] == "power_budget_warning"]
        assert len(warnings) == 1
        assert warnings[0]["deficit"] == pytest.approx(0.3)

    def test_multiple_agents_below_budget(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.5
        WORLD["agents"]["rover-mistral"]["battery"] = 0.2
        WORLD["power_budgets"]["drone-mistral"] = 0.4
        WORLD["agents"]["drone-mistral"]["battery"] = 0.1
        events = check_power_budgets(tick=10)
        warnings = [e for e in events if e["type"] == "power_budget_warning"]
        warned_ids = {w["agent_id"] for w in warnings}
        assert warned_ids == {"rover-mistral", "drone-mistral"}


# ── T012: EmergencyMode event tests ──────────────────────────────────────────

# Agents available for creating high-demand scenarios.
_FIELD_AGENTS = [
    "rover-mistral",
    "rover-2",
    "drone-mistral",
    "hauler-mistral",
    "rover-large",
    "rover-medium",
    "rover-codestral",
]


class TestEmergencyMode:
    """T012: EmergencyMode event tests."""

    def test_emergency_activated_when_demand_exceeds_capacity(self):
        # Set high budgets for multiple agents with low batteries.
        for agent_id in _FIELD_AGENTS:
            WORLD["power_budgets"][agent_id] = 0.5
            WORLD["agents"][agent_id]["battery"] = 0.1
        # Total demand = 7 * 0.4 = 2.8 > STATION_POWER_CAPACITY (1.0)
        events = check_power_budgets(tick=10)
        activated = [e for e in events if e["type"] == "emergency_mode_activated"]
        assert len(activated) == 1
        assert activated[0]["total_demand"] > STATION_POWER_CAPACITY
        assert WORLD["emergency_mode"] is True

    def test_no_emergency_when_demand_within_capacity(self):
        WORLD["power_budgets"]["rover-mistral"] = 0.3
        WORLD["agents"]["rover-mistral"]["battery"] = 0.2
        # Demand = 0.1 < 1.0
        events = check_power_budgets(tick=10)
        activated = [e for e in events if e["type"] == "emergency_mode_activated"]
        assert len(activated) == 0
        assert WORLD["emergency_mode"] is False

    def test_emergency_deactivated_when_demand_drops(self):
        # First activate emergency mode.
        for agent_id in _FIELD_AGENTS:
            WORLD["power_budgets"][agent_id] = 0.5
            WORLD["agents"][agent_id]["battery"] = 0.1
        check_power_budgets(tick=10)
        assert WORLD["emergency_mode"] is True

        # Now charge agents to reduce demand below capacity.
        for agent_id in _FIELD_AGENTS:
            WORLD["agents"][agent_id]["battery"] = 0.8
        events = check_power_budgets(tick=14)
        deactivated = [e for e in events if e["type"] == "emergency_mode_deactivated"]
        assert len(deactivated) == 1
        assert WORLD["emergency_mode"] is False

    def test_emergency_flag_toggled_in_world(self):
        assert WORLD["emergency_mode"] is False
        for agent_id in _FIELD_AGENTS:
            WORLD["power_budgets"][agent_id] = 0.5
            WORLD["agents"][agent_id]["battery"] = 0.1
        check_power_budgets(tick=10)
        assert WORLD["emergency_mode"] is True

    def test_emergency_not_triggered_when_demand_equals_capacity(self):
        # Carefully set up demand exactly equal to capacity.
        # 2 agents with deficit 0.5 each => demand = 1.0 == STATION_POWER_CAPACITY.
        WORLD["power_budgets"]["rover-mistral"] = 0.6
        WORLD["agents"]["rover-mistral"]["battery"] = 0.1
        WORLD["power_budgets"]["rover-2"] = 0.6
        WORLD["agents"]["rover-2"]["battery"] = 0.1
        # demand = 0.5 + 0.5 = 1.0, not strictly greater than 1.0
        events = check_power_budgets(tick=10)
        activated = [e for e in events if e["type"] == "emergency_mode_activated"]
        assert len(activated) == 0
        assert WORLD["emergency_mode"] is False

    def test_emergency_activated_includes_agents_in_deficit(self):
        for agent_id in _FIELD_AGENTS:
            WORLD["power_budgets"][agent_id] = 0.5
            WORLD["agents"][agent_id]["battery"] = 0.1
        events = check_power_budgets(tick=10)
        activated = [e for e in events if e["type"] == "emergency_mode_activated"]
        assert "agents_in_deficit" in activated[0]
        deficit_ids = {a["agent_id"] for a in activated[0]["agents_in_deficit"]}
        assert deficit_ids == set(_FIELD_AGENTS)
