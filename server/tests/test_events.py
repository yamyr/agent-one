"""Tests for scripted event timeline (server/app/events.py)."""

import json
import os
import tempfile

import pytest

from app.events import ScriptedEvent, ScriptedTimeline, DEMO_TIMELINE, _EXECUTORS
from app.world import WORLD, reset_world


@pytest.fixture(autouse=True)
def _fresh_world():
    reset_world()
    yield
    reset_world()


# ── ScriptedEvent model ────────────────────────────────────────────────────


class TestScriptedEventModel:
    def test_valid_event(self):
        e = ScriptedEvent(tick=5, type="storm_start", payload={"duration": 10})
        assert e.tick == 5
        assert e.type == "storm_start"
        assert e.payload == {"duration": 10}
        assert e.fired is False

    def test_default_payload_is_empty_dict(self):
        e = ScriptedEvent(tick=0, type="storm_end")
        assert e.payload == {}

    def test_description_field(self):
        e = ScriptedEvent(tick=1, type="broadcast", description="Test broadcast")
        assert e.description == "Test broadcast"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValueError, match="Unknown event type"):
            ScriptedEvent(tick=0, type="invalid_event_type")

    def test_negative_tick_rejected(self):
        with pytest.raises(ValueError):
            ScriptedEvent(tick=-1, type="storm_start")

    def test_all_valid_types_accepted(self):
        valid_types = [
            "storm_start",
            "storm_end",
            "resource_spawn",
            "battery_drain",
            "battery_set",
            "agent_message",
            "broadcast",
            "spawn_obstacle",
            "mission_update",
        ]
        for t in valid_types:
            e = ScriptedEvent(tick=0, type=t)
            assert e.type == t


# ── ScriptedTimeline load/clear/reset ──────────────────────────────────────


class TestTimelineLoadClearReset:
    def test_load_events(self):
        tl = ScriptedTimeline()
        count = tl.load(
            [
                {"tick": 5, "type": "storm_start", "payload": {"duration": 10}},
                {"tick": 10, "type": "storm_end"},
            ]
        )
        assert count == 2
        assert len(tl.events) == 2
        assert tl.pending_count == 2
        assert tl.fired_count == 0

    def test_load_sorts_by_tick(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {"tick": 20, "type": "storm_end"},
                {"tick": 5, "type": "storm_start"},
                {"tick": 10, "type": "broadcast", "payload": {"name": "test", "event_payload": {}}},
            ]
        )
        ticks = [e.tick for e in tl.events]
        assert ticks == [5, 10, 20]

    def test_load_skips_invalid_entries(self):
        tl = ScriptedTimeline()
        count = tl.load(
            [
                {"tick": 5, "type": "storm_start"},
                {"tick": -1, "type": "storm_end"},
                {"tick": 10, "type": "invalid_type"},
                {"tick": 15, "type": "storm_end"},
            ]
        )
        assert count == 2
        assert len(tl.events) == 2

    def test_clear_removes_all(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 5, "type": "storm_start"}])
        tl.clear()
        assert len(tl.events) == 0
        assert tl.pending_count == 0

    def test_reset_marks_unfired(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 1, "type": "storm_end"}])
        tl.check_tick(1, WORLD)
        assert tl.fired_count == 1
        tl.reset()
        assert tl.fired_count == 0
        assert tl.pending_count == 1

    def test_load_replaces_previous(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 5, "type": "storm_start"}])
        tl.load([{"tick": 10, "type": "storm_end"}, {"tick": 20, "type": "storm_start"}])
        assert len(tl.events) == 2
        assert tl.events[0].tick == 10


# ── ScriptedTimeline check_tick ────────────────────────────────────────────


class TestTimelineCheckTick:
    def test_fires_event_at_matching_tick(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 5, "type": "storm_end"}])
        results = tl.check_tick(5, WORLD)
        assert len(results) == 1
        assert results[0]["name"] == "scripted_storm_ended"

    def test_does_not_fire_before_tick(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 10, "type": "storm_end"}])
        results = tl.check_tick(5, WORLD)
        assert len(results) == 0
        assert tl.pending_count == 1

    def test_fires_missed_events_on_skip(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {"tick": 3, "type": "storm_end"},
                {"tick": 5, "type": "storm_start", "payload": {"duration": 10}},
                {"tick": 10, "type": "storm_end"},
            ]
        )
        results = tl.check_tick(7, WORLD)
        assert len(results) == 2
        assert tl.fired_count == 2
        assert tl.pending_count == 1

    def test_fires_multiple_events_at_same_tick(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {"tick": 5, "type": "storm_end"},
                {
                    "tick": 5,
                    "type": "battery_drain",
                    "payload": {"agent_id": "rover-mistral", "amount": 0.1},
                },
            ]
        )
        results = tl.check_tick(5, WORLD)
        assert len(results) == 2

    def test_event_fires_only_once(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 5, "type": "storm_end"}])
        tl.check_tick(5, WORLD)
        results = tl.check_tick(5, WORLD)
        assert len(results) == 0

    def test_empty_timeline_returns_nothing(self):
        tl = ScriptedTimeline()
        results = tl.check_tick(100, WORLD)
        assert results == []


# ── Individual executor tests ──────────────────────────────────────────────


class TestStormStartExecutor:
    def test_sets_storm_warning_phase(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 1, "type": "storm_start", "payload": {"duration": 15, "intensity": 0.7}}])
        results = tl.check_tick(1, WORLD)
        assert len(results) == 1
        assert WORLD["storm"]["phase"] == "warning"
        assert WORLD["storm"]["active_end"] - WORLD["storm"]["active_start"] == 15

    def test_result_has_scripted_flag(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 1, "type": "storm_start"}])
        results = tl.check_tick(1, WORLD)
        assert results[0]["payload"]["scripted"] is True


class TestStormEndExecutor:
    def test_clears_active_storm(self):
        WORLD["storm"]["phase"] = "active"
        WORLD["storm"]["intensity"] = 0.8
        tl = ScriptedTimeline()
        tl.load([{"tick": 1, "type": "storm_end"}])
        results = tl.check_tick(1, WORLD)
        assert len(results) == 1
        assert WORLD["storm"]["phase"] == "clear"
        assert WORLD["storm"]["intensity"] == 0.0

    def test_clears_when_no_storm_exists(self):
        tl = ScriptedTimeline()
        tl.load([{"tick": 1, "type": "storm_end"}])
        results = tl.check_tick(1, WORLD)
        assert len(results) == 1


class TestResourceSpawnExecutor:
    def test_spawns_basalt_vein(self):
        initial_count = len(WORLD.get("stones", []))
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "resource_spawn",
                    "payload": {
                        "resource_type": "basalt_vein",
                        "position": [7, 3],
                        "grade": "rich",
                        "quantity": 500,
                    },
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert len(WORLD["stones"]) == initial_count + 1
        spawned = WORLD["stones"][-1]
        assert spawned["position"] == [7, 3]
        assert spawned["grade"] == "rich"
        assert spawned["quantity"] == 500
        assert spawned["analyzed"] is True

    def test_spawns_ice_deposit(self):
        initial_count = len(WORLD.get("ice_deposits", []))
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "resource_spawn",
                    "payload": {
                        "resource_type": "ice",
                        "position": [2, -1],
                        "quantity": 30,
                    },
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert len(WORLD["ice_deposits"]) == initial_count + 1
        spawned = WORLD["ice_deposits"][-1]
        assert spawned["position"] == [2, -1]
        assert spawned["quantity"] == 30


class TestBatteryDrainExecutor:
    def test_drains_agent_battery(self):
        WORLD["agents"]["rover-mistral"]["battery"] = 0.8
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "battery_drain",
                    "payload": {"agent_id": "rover-mistral", "amount": 0.3},
                }
            ]
        )
        results = tl.check_tick(1, WORLD)
        assert abs(WORLD["agents"]["rover-mistral"]["battery"] - 0.5) < 0.001
        assert results[0]["payload"]["battery_before"] == 0.8

    def test_battery_does_not_go_negative(self):
        WORLD["agents"]["rover-mistral"]["battery"] = 0.1
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "battery_drain",
                    "payload": {"agent_id": "rover-mistral", "amount": 0.5},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert WORLD["agents"]["rover-mistral"]["battery"] == 0.0

    def test_unknown_agent_returns_error(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "battery_drain",
                    "payload": {"agent_id": "nonexistent", "amount": 0.1},
                }
            ]
        )
        results = tl.check_tick(1, WORLD)
        assert "error" in results[0]["payload"]


class TestBatterySetExecutor:
    def test_sets_battery_level(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "battery_set",
                    "payload": {"agent_id": "drone-mistral", "level": 0.42},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert abs(WORLD["agents"]["drone-mistral"]["battery"] - 0.42) < 0.001

    def test_clamps_to_valid_range(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "battery_set",
                    "payload": {"agent_id": "rover-mistral", "level": 1.5},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert WORLD["agents"]["rover-mistral"]["battery"] == 1.0


class TestAgentMessageExecutor:
    def test_sends_message(self):
        from app.world import AGENT_MESSAGES

        initial_count = len(AGENT_MESSAGES)
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "agent_message",
                    "payload": {
                        "from": "station",
                        "to": "rover-mistral",
                        "message": "Return to base immediately.",
                    },
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert len(AGENT_MESSAGES) == initial_count + 1
        msg = AGENT_MESSAGES[-1]
        assert msg["from"] == "station"
        assert msg["to"] == "rover-mistral"
        assert msg["message"] == "Return to base immediately."


class TestBroadcastExecutor:
    def test_returns_custom_event(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "broadcast",
                    "payload": {
                        "name": "custom_alert",
                        "event_payload": {"severity": "high"},
                    },
                }
            ]
        )
        results = tl.check_tick(1, WORLD)
        assert results[0]["name"] == "custom_alert"
        assert results[0]["payload"]["severity"] == "high"
        assert results[0]["payload"]["scripted"] is True


class TestSpawnObstacleExecutor:
    def test_spawns_mountain(self):
        initial_count = len(WORLD.get("obstacles", []))
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "spawn_obstacle",
                    "payload": {"kind": "mountain", "position": [15, 15]},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert len(WORLD["obstacles"]) == initial_count + 1
        spawned = WORLD["obstacles"][-1]
        assert spawned["kind"] == "mountain"
        assert spawned["position"] == [15, 15]

    def test_spawns_geyser_with_cycle_tick(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "spawn_obstacle",
                    "payload": {"kind": "geyser", "position": [12, 8]},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        spawned = WORLD["obstacles"][-1]
        assert spawned["kind"] == "geyser"
        assert "_cycle_tick" in spawned


class TestMissionUpdateExecutor:
    def test_updates_target_quantity(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "mission_update",
                    "payload": {"target_quantity": 150},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert WORLD["mission"]["target_quantity"] == 150

    def test_updates_collected_quantity(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "mission_update",
                    "payload": {"collected_quantity": 50},
                }
            ]
        )
        tl.check_tick(1, WORLD)
        assert WORLD["mission"]["collected_quantity"] == 50


# ── File loading ───────────────────────────────────────────────────────────


class TestFileLoading:
    def test_load_from_json_array_file(self):
        tl = ScriptedTimeline()
        events = [
            {"tick": 5, "type": "storm_start", "payload": {"duration": 10}},
            {"tick": 10, "type": "storm_end"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(events, f)
            f.flush()
            count = tl.load_from_file(f.name)
        os.unlink(f.name)
        assert count == 2

    def test_load_from_json_object_file(self):
        tl = ScriptedTimeline()
        data = {
            "events": [
                {"tick": 1, "type": "storm_end"},
                {"tick": 2, "type": "storm_start"},
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            count = tl.load_from_file(f.name)
        os.unlink(f.name)
        assert count == 2

    def test_load_from_nonexistent_file(self):
        tl = ScriptedTimeline()
        count = tl.load_from_file("/nonexistent/path.json")
        assert count == 0

    def test_load_from_invalid_json(self):
        tl = ScriptedTimeline()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            count = tl.load_from_file(f.name)
        os.unlink(f.name)
        assert count == 0


# ── get_status ─────────────────────────────────────────────────────────────


class TestGetStatus:
    def test_status_structure(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {"tick": 5, "type": "storm_start"},
                {"tick": 10, "type": "storm_end"},
            ]
        )
        status = tl.get_status()
        assert status["total_events"] == 2
        assert status["fired"] == 0
        assert status["pending"] == 2
        assert len(status["events"]) == 2

    def test_status_after_firing(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {"tick": 1, "type": "storm_end"},
                {"tick": 10, "type": "storm_start"},
            ]
        )
        tl.check_tick(1, WORLD)
        status = tl.get_status()
        assert status["fired"] == 1
        assert status["pending"] == 1


# ── Demo timeline ─────────────────────────────────────────────────────────


class TestDemoTimeline:
    def test_demo_timeline_is_valid(self):
        tl = ScriptedTimeline()
        count = tl.load(DEMO_TIMELINE)
        assert count == len(DEMO_TIMELINE)
        assert count > 0

    def test_demo_events_sorted_by_tick(self):
        tl = ScriptedTimeline()
        tl.load(DEMO_TIMELINE)
        ticks = [e.tick for e in tl.events]
        assert ticks == sorted(ticks)

    def test_demo_events_all_have_descriptions(self):
        for entry in DEMO_TIMELINE:
            assert "description" in entry
            assert len(entry["description"]) > 0


# ── Executor registry ─────────────────────────────────────────────────────


class TestExecutorRegistry:
    def test_all_event_types_have_executors(self):
        valid_types = [
            "storm_start",
            "storm_end",
            "resource_spawn",
            "battery_drain",
            "battery_set",
            "agent_message",
            "broadcast",
            "spawn_obstacle",
            "mission_update",
        ]
        for t in valid_types:
            assert t in _EXECUTORS, f"Missing executor for {t}"

    def test_executors_are_callable(self):
        for name, executor in _EXECUTORS.items():
            assert callable(executor), f"Executor {name} is not callable"


# ── Integration: world.next_tick returns timeline events ───────────────────


class TestWorldIntegration:
    def test_next_tick_returns_three_tuple(self):
        from app.world import next_tick

        result = next_tick()
        assert len(result) == 3
        tick, power_events, timeline_events = result
        assert isinstance(tick, int)
        assert isinstance(power_events, list)
        assert isinstance(timeline_events, list)

    def test_timeline_events_fired_via_next_tick(self):
        from app.events import timeline
        from app.world import next_tick, WORLD

        timeline.load([{"tick": WORLD["tick"] + 1, "type": "storm_end"}])
        tick, _pe, te = next_tick()
        assert len(te) == 1
        assert te[0]["name"] == "scripted_storm_ended"
        timeline.clear()


# ── Preset integration ─────────────────────────────────────────────────────


class TestPresetIntegration:
    def test_demo_timeline_preset_exists(self):
        from app.presets import PRESETS

        assert "demo_timeline" in PRESETS

    def test_demo_timeline_preset_fields(self):
        from app.presets import PRESETS

        preset = PRESETS["demo_timeline"]
        assert preset["name"] == "demo_timeline"
        assert (
            "scripted" in preset["description"].lower() or "demo" in preset["description"].lower()
        )
        assert preset["world_overrides"]["mission"]["target_quantity"] == 200


# ── Config integration ─────────────────────────────────────────────────────


class TestConfigIntegration:
    def test_event_script_config_field_exists(self):
        from app.config import settings

        assert hasattr(settings, "event_script")

    def test_event_script_default_empty(self):
        from app.config import settings

        assert settings.event_script == ""


# ── Event description tagging ──────────────────────────────────────────────


class TestDescriptionTagging:
    def test_description_included_in_result(self):
        tl = ScriptedTimeline()
        tl.load(
            [
                {
                    "tick": 1,
                    "type": "storm_end",
                    "description": "Clear the skies",
                }
            ]
        )
        results = tl.check_tick(1, WORLD)
        assert results[0]["payload"]["description"] == "Clear the skies"
