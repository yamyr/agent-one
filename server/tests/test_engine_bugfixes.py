"""Regression tests for simulation engine bugfixes (issue #191).

Covers 8 fixes:
1. Tick inflation guard (next_tick idempotency within 1s window)
2. Tool whitelist completeness (drop_item, request_confirm)
3. Mountain path checking in move_agent (intermediate tiles)
4. Ice-to-water conversion ratio (multiply, not divide)
5. Drone scan auto-relay field name + multi-rover target
6. Station memory cap via record_memory
7. Geyser per-tick damage (every erupting tick, not just first)
8. Storm multiplier on refinery and upgrade actions
"""

import copy
import time
import unittest

from app.world import (
    WORLD,
    BATTERY_COST_USE_REFINERY,
    BATTERY_COST_UPGRADE,
    GEYSER_CYCLE_IDLE,
    GEYSER_CYCLE_WARNING,
    ICE_TO_WATER_RATIO,
    MEMORY_MAX,
    UPGRADE_BASALT_COST,
    check_mission_status,
    move_agent,
    next_tick,
    record_memory,
    reset_world,
    update_geysers,
)
from app import world as world_mod


class _WorldSaveRestore(unittest.TestCase):
    def setUp(self):
        self._saved_world = copy.deepcopy(WORLD)
        self._saved_last_tick_time = world_mod._last_tick_time

    def tearDown(self):
        WORLD.clear()
        WORLD.update(self._saved_world)
        world_mod._last_tick_time = self._saved_last_tick_time


# ---------- Fix 1: Tick inflation guard ----------


class TestTickInflationGuard(_WorldSaveRestore):
    def test_first_call_advances_tick(self):
        world_mod._last_tick_time = 0.0
        old_tick = WORLD["tick"]
        tick, events, _tl = next_tick()
        self.assertEqual(tick, old_tick + 1)

    def test_rapid_calls_are_idempotent(self):
        world_mod._last_tick_time = 0.0
        old_tick = WORLD["tick"]
        tick1, _, _tl1 = next_tick()
        tick2, _, _tl2 = next_tick()
        self.assertEqual(tick1, old_tick + 1)
        self.assertEqual(tick2, tick1, "Second rapid call should NOT advance tick")

    def test_reset_world_clears_tick_guard(self):
        world_mod._last_tick_time = time.monotonic()
        reset_world()
        self.assertEqual(world_mod._last_tick_time, 0.0)
        old_tick = WORLD["tick"]
        tick, _, _tl = next_tick()
        self.assertEqual(tick, old_tick + 1)


# ---------- Fix 2: Tool whitelist ----------


class TestToolWhitelist(unittest.TestCase):
    def test_mistral_rover_whitelist_includes_drop_item_and_request_confirm(self):
        from app.agent import MistralRoverReasoner
        import inspect

        source = inspect.getsource(MistralRoverReasoner.run_turn)
        self.assertIn("drop_item", source)
        self.assertIn("request_confirm", source)

    def test_hf_rover_whitelist_includes_drop_item_and_request_confirm(self):
        from app.agent import HuggingFaceRoverReasoner
        import inspect

        source = inspect.getsource(HuggingFaceRoverReasoner.run_turn)
        self.assertIn("drop_item", source)
        self.assertIn("request_confirm", source)


# ---------- Fix 3: Mountain path checking ----------


class TestMountainPathBlocking(_WorldSaveRestore):
    def setUp(self):
        super().setUp()
        agent = WORLD["agents"]["rover-mistral"]
        agent["position"] = [5, 10]
        agent["battery"] = 1.0
        agent["visited"] = [[5, 10]]
        agent["mission"] = {"objective": "test", "plan": []}

    def test_mountain_on_intermediate_tile_blocks_move(self):
        WORLD.setdefault("obstacles", []).append({"position": [6, 10], "kind": "mountain"})
        result = move_agent("rover-mistral", 8, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Mountain", result["error"])
        self.assertIn("(6, 10)", result["error"])

    def test_mountain_on_destination_blocks_move(self):
        WORLD.setdefault("obstacles", []).append({"position": [7, 10], "kind": "mountain"})
        result = move_agent("rover-mistral", 7, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Mountain", result["error"])

    def test_no_mountain_allows_move(self):
        result = move_agent("rover-mistral", 6, 10)
        self.assertTrue(result["ok"])


# ---------- Fix 4: Ice conversion ratio ----------


class TestIceConversionRatio(_WorldSaveRestore):
    def setUp(self):
        super().setUp()
        station_pos = WORLD["agents"]["station"]["position"]
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = list(station_pos)
        rover["battery"] = 1.0
        rover["inventory"] = [{"type": "ice", "quantity": 10}]
        WORLD["station_resources"] = {"water": 0, "gas": 0, "parts": []}
        mission = WORLD.get("mission", {})
        mission["target_type"] = "basalt_vein"
        mission["target_quantity"] = 9999
        WORLD["mission"] = mission

    def test_ice_produces_water_by_multiplication(self):
        check_mission_status()
        water = WORLD["station_resources"]["water"]
        expected = 10 * ICE_TO_WATER_RATIO
        self.assertEqual(
            water, expected, f"10 ice * {ICE_TO_WATER_RATIO} should give {expected} water"
        )


# ---------- Fix 5: Drone scan auto-relay ----------


class TestDroneScanAutoRelay(unittest.TestCase):
    def test_scan_result_uses_peak_field(self):
        from app.world import _execute_scan

        saved = copy.deepcopy(WORLD)
        try:
            drone = WORLD["agents"].get("drone-mistral")
            if drone is None:
                self.skipTest("No drone-mistral agent in WORLD")
            drone["battery"] = 1.0
            result = _execute_scan("drone-mistral", drone)
            if result["ok"]:
                self.assertIn("peak", result, "Scan result must have 'peak' field")
                self.assertNotIn(
                    "concentration",
                    result,
                    "Scan result should NOT have 'concentration' field",
                )
        finally:
            WORLD.clear()
            WORLD.update(saved)


# ---------- Fix 6: Station memory cap ----------


class TestStationMemoryCap(_WorldSaveRestore):
    def test_record_memory_enforces_cap(self):
        WORLD["agents"]["station"] = WORLD.get("agents", {}).get(
            "station",
            {"type": "station", "position": [0, 0], "battery": 1.0, "memory": []},
        )
        WORLD["agents"]["station"]["memory"] = []

        for i in range(MEMORY_MAX + 5):
            record_memory("station", f"memory {i}")

        mem = WORLD["agents"]["station"]["memory"]
        self.assertLessEqual(
            len(mem),
            MEMORY_MAX,
            f"Station memory should be capped at {MEMORY_MAX}, got {len(mem)}",
        )
        self.assertIn(f"memory {MEMORY_MAX + 4}", mem[-1])


# ---------- Fix 7: Geyser per-tick damage ----------


class TestGeyserPerTickDamage(_WorldSaveRestore):
    def setUp(self):
        super().setUp()
        WORLD["obstacles"] = []
        agent = WORLD["agents"]["rover-mistral"]
        gx, gy = agent["position"]
        agent["battery"] = 1.0
        erupting_start = GEYSER_CYCLE_IDLE + GEYSER_CYCLE_WARNING
        WORLD["obstacles"].append(
            {
                "position": [gx, gy],
                "kind": "geyser",
                "state": "warning",
                "_cycle_tick": erupting_start - 1,
            }
        )
        WORLD["structures"] = [s for s in WORLD.get("structures", []) if s["position"] != [gx, gy]]

    def test_damage_on_first_erupting_tick(self):
        agent = WORLD["agents"]["rover-mistral"]
        before = agent["battery"]
        events = update_geysers()
        after = agent["battery"]
        self.assertLess(after, before, "Battery should decrease on first erupting tick")
        eruption_events = [e for e in events if e.get("type") == "geyser_eruption"]
        self.assertGreater(len(eruption_events), 0, "Should emit geyser_eruption event")

    def test_damage_on_subsequent_erupting_tick(self):
        agent = WORLD["agents"]["rover-mistral"]

        update_geysers()
        battery_after_first = agent["battery"]

        update_geysers()
        battery_after_second = agent["battery"]

        self.assertLess(
            battery_after_second,
            battery_after_first,
            "Battery should decrease on subsequent erupting ticks too",
        )


# ---------- Fix 8: Storm multiplier on refinery/upgrade ----------


class TestStormMultiplierRefinery(_WorldSaveRestore):
    def setUp(self):
        super().setUp()
        agent = WORLD["agents"]["rover-mistral"]
        agent["position"] = [5, 5]
        agent["battery"] = 1.0
        agent["inventory"] = [{"type": "basalt_vein", "quantity": 100, "grade": "high"}]
        WORLD.setdefault("structures", []).append(
            {
                "type": "refinery",
                "position": [5, 6],
                "active": True,
                "explored": True,
                "category": "resource_processing",
                "description": "A refinery",
                "contents": {"processing_capacity": 50},
            }
        )

    def test_refinery_uses_storm_multiplied_cost(self):
        WORLD["storm"] = {"phase": "active", "intensity": 1.0}
        agent = WORLD["agents"]["rover-mistral"]
        agent["battery"] = 1.0

        from app.world import _execute_use_refinery

        result = _execute_use_refinery("rover-mistral", agent)

        if result["ok"]:
            battery_used = 1.0 - agent["battery"]
            self.assertGreater(
                battery_used,
                BATTERY_COST_USE_REFINERY,
                "Storm should increase refinery battery cost",
            )

    def test_refinery_works_without_storm(self):
        WORLD["storm"] = {"phase": "clear", "intensity": 0.0}
        agent = WORLD["agents"]["rover-mistral"]
        agent["battery"] = 1.0

        from app.world import _execute_use_refinery

        result = _execute_use_refinery("rover-mistral", agent)
        self.assertTrue(result["ok"], f"Refinery should succeed without storm: {result}")
        battery_used = 1.0 - agent["battery"]
        self.assertAlmostEqual(
            battery_used,
            BATTERY_COST_USE_REFINERY,
            places=6,
            msg="Without storm, should use exact base cost",
        )


class TestStormMultiplierUpgrade(_WorldSaveRestore):
    def setUp(self):
        super().setUp()
        agent = WORLD["agents"]["rover-mistral"]
        agent["position"] = [5, 5]
        agent["battery"] = 1.0
        agent["inventory"] = [
            {"type": "basalt_vein", "quantity": 50, "grade": "high"}
            for _ in range(UPGRADE_BASALT_COST + 1)
        ]
        WORLD.setdefault("structures", []).append(
            {
                "type": "refinery",
                "position": [5, 6],
                "active": True,
                "explored": True,
                "upgrade_level": 1,
                "category": "resource_processing",
                "description": "A refinery",
                "contents": {"processing_capacity": 50},
            }
        )

    def test_upgrade_uses_storm_multiplied_cost(self):
        WORLD["storm"] = {"phase": "active", "intensity": 1.0}
        agent = WORLD["agents"]["rover-mistral"]
        agent["battery"] = 1.0

        from app.world import _execute_upgrade_building

        result = _execute_upgrade_building("rover-mistral", agent, {})

        if result["ok"]:
            battery_used = 1.0 - agent["battery"]
            self.assertGreater(
                battery_used,
                BATTERY_COST_UPGRADE,
                "Storm should increase upgrade battery cost",
            )

    def test_upgrade_works_without_storm(self):
        WORLD["storm"] = {"phase": "clear", "intensity": 0.0}
        agent = WORLD["agents"]["rover-mistral"]
        agent["battery"] = 1.0

        from app.world import _execute_upgrade_building

        result = _execute_upgrade_building("rover-mistral", agent, {})
        self.assertTrue(result["ok"], f"Upgrade should succeed without storm: {result}")
        battery_used = 1.0 - agent["battery"]
        self.assertAlmostEqual(
            battery_used,
            BATTERY_COST_UPGRADE,
            places=6,
            msg="Without storm, should use exact base cost",
        )


if __name__ == "__main__":
    unittest.main()
