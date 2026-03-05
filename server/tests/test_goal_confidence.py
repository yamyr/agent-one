"""Tests for goal confidence tracking — update logic, clamping, and mission reset."""

import pytest


@pytest.fixture(autouse=True)
def _reset_world():
    """Reset WORLD state before each test."""
    from app.world import WORLD, _build_initial_world

    initial = _build_initial_world()
    WORLD.clear()
    WORLD.update(initial)
    yield
    WORLD.clear()
    WORLD.update(_build_initial_world())


class TestGoalConfidenceInit:
    """Verify goal_confidence is initialized for all agent types."""

    def test_rover_has_confidence(self):
        from app.world import WORLD

        rover = WORLD["agents"]["rover-mistral"]
        assert rover["goal_confidence"] == 0.5

    def test_hauler_has_confidence(self):
        from app.world import WORLD

        hauler = WORLD["agents"]["hauler-mistral"]
        assert hauler["goal_confidence"] == 0.5

    def test_drone_has_confidence(self):
        from app.world import WORLD

        drone = WORLD["agents"]["drone-mistral"]
        assert drone["goal_confidence"] == 0.5

    def test_station_has_confidence(self):
        from app.world import WORLD

        station = WORLD["agents"]["station"]
        assert station["goal_confidence"] == 0.5


class TestUpdateGoalConfidence:
    """Verify update_goal_confidence applies delta and clamps."""

    def test_increase_on_success(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.5
        result = update_goal_confidence("rover-mistral", 0.05)
        assert result == pytest.approx(0.55)
        assert WORLD["agents"]["rover-mistral"]["goal_confidence"] == pytest.approx(0.55)

    def test_decrease_on_failure(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.5
        result = update_goal_confidence("rover-mistral", -0.05)
        assert result == pytest.approx(0.45)

    def test_decrease_on_fallback(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.5
        result = update_goal_confidence("rover-mistral", -0.08)
        assert result == pytest.approx(0.42)

    def test_decrease_on_hazard(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.6
        result = update_goal_confidence("rover-mistral", -0.08)
        assert result == pytest.approx(0.52)

    def test_increase_on_delivery(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.7
        result = update_goal_confidence("rover-mistral", 0.10)
        assert result == pytest.approx(0.8)

    def test_clamp_upper_bound(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.98
        result = update_goal_confidence("rover-mistral", 0.10)
        assert result == 1.0

    def test_clamp_lower_bound(self):
        from app.world import WORLD, update_goal_confidence

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.02
        result = update_goal_confidence("rover-mistral", -0.10)
        assert result == 0.0

    def test_unknown_agent_returns_default(self):
        from app.world import update_goal_confidence

        result = update_goal_confidence("nonexistent-agent", 0.05)
        assert result == 0.5


class TestMissionResetConfidence:
    """Verify confidence resets to 0.5 on mission assignment."""

    def test_assign_mission_resets_confidence(self):
        from app.world import WORLD, assign_mission

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.9
        assign_mission("rover-mistral", "New mission objective")
        assert WORLD["agents"]["rover-mistral"]["goal_confidence"] == 0.5

    def test_assign_mission_resets_low_confidence(self):
        from app.world import WORLD, assign_mission

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.1
        assign_mission("rover-mistral", "Another mission")
        assert WORLD["agents"]["rover-mistral"]["goal_confidence"] == 0.5


class TestObservationContextConfidence:
    """Verify goal_confidence is included in observation contexts."""

    def test_observe_rover_includes_confidence(self):
        from app.world import WORLD, observe_rover

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.73
        ctx = observe_rover("rover-mistral")
        assert ctx.agent.goal_confidence == pytest.approx(0.73)

    def test_observe_hauler_includes_confidence(self):
        from app.world import WORLD, observe_hauler

        WORLD["agents"]["hauler-mistral"]["goal_confidence"] = 0.35
        ctx = observe_hauler("hauler-mistral")
        assert ctx.agent.goal_confidence == pytest.approx(0.35)

    def test_observe_station_includes_rover_confidence(self):
        from app.world import WORLD, observe_station

        WORLD["agents"]["rover-mistral"]["goal_confidence"] = 0.82
        ctx = observe_station()
        rover_summaries = [r for r in ctx.rovers if r.id == "rover-mistral"]
        assert len(rover_summaries) == 1
        assert rover_summaries[0].goal_confidence == pytest.approx(0.82)


class TestTrainingDataConfidence:
    """Verify goal_confidence fields in training data models."""

    def test_turn_world_snapshot_has_confidence(self):
        from app.training_models import TurnWorldSnapshot

        snap = TurnWorldSnapshot(goal_confidence=0.65)
        assert snap.goal_confidence == pytest.approx(0.65)

    def test_training_turn_has_confidence_before_after(self):
        from app.training_models import TrainingTurn

        turn = TrainingTurn(goal_confidence_before=0.5, goal_confidence_after=0.55)
        assert turn.goal_confidence_before == pytest.approx(0.5)
        assert turn.goal_confidence_after == pytest.approx(0.55)

    def test_turn_world_snapshot_default(self):
        from app.training_models import TurnWorldSnapshot

        snap = TurnWorldSnapshot()
        assert snap.goal_confidence == 0.5

    def test_training_turn_default(self):
        from app.training_models import TrainingTurn

        turn = TrainingTurn()
        assert turn.goal_confidence_before == 0.5
        assert turn.goal_confidence_after == 0.5
