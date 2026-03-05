"""Expanded test coverage for collect_gas, hauler loop, station recall,
resource lifecycle, upgrade edge cases, and storm battery effects.

Feature 186: covers critical test gaps identified via code analysis.
"""

import copy
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.world import (
    BATTERY_COST_COLLECT_GAS,
    UPGRADES,
    WORLD,
    _ensure_stone_index,
    _stone_index,
    execute_action,
)
from app.station import execute_action as station_execute_action
from app import storm as storm_mod


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _place_analyzed_stone(x, y, grade="high", quantity=200):
    """Place an analyzed stone at (x, y) and update the spatial index."""
    stone = {
        "position": [x, y],
        "type": "basalt_vein",
        "_true_type": "basalt_vein",
        "grade": grade,
        "_true_grade": grade,
        "quantity": quantity,
        "_true_quantity": quantity,
        "analyzed": True,
    }
    _ensure_stone_index()
    WORLD.setdefault("stones", []).append(stone)
    _stone_index[(x, y)] = stone
    return stone


def _place_unanalyzed_stone(x, y, grade="high", quantity=200):
    """Place an unanalyzed stone at (x, y) and update the spatial index."""
    stone = {
        "position": [x, y],
        "type": "unknown",
        "_true_type": "basalt_vein",
        "grade": "unknown",
        "_true_grade": grade,
        "quantity": 0,
        "_true_quantity": quantity,
        "analyzed": False,
    }
    _ensure_stone_index()
    WORLD.setdefault("stones", []).append(stone)
    _stone_index[(x, y)] = stone
    return stone


def _make_gas_plant(pos, gas_stored=50, active=True):
    """Create a gas plant structure dict."""
    return {
        "type": "gas_plant",
        "position": list(pos),
        "active": active,
        "contents": {"gas_stored": gas_stored},
    }


class _WorldSaveRestore(unittest.TestCase):
    """Base class that saves and restores WORLD state around each test."""

    def setUp(self):
        self._saved_world = {
            "station_upgrades": copy.deepcopy(WORLD.get("station_upgrades", {})),
            "station_resources": copy.deepcopy(
                WORLD.get("station_resources", {"water": 0, "gas": 0, "parts": []})
            ),
            "structures": copy.deepcopy(WORLD.get("structures", [])),
            "stones": copy.deepcopy(WORLD.get("stones", [])),
            "ground_items": copy.deepcopy(WORLD.get("ground_items", [])),
            "delivered_items": copy.deepcopy(WORLD.get("delivered_items", [])),
            "storm": copy.deepcopy(WORLD.get("storm", storm_mod.make_storm_state())),
        }
        self._saved_rover = copy.deepcopy(WORLD["agents"]["rover-mistral"])
        self._saved_hauler = copy.deepcopy(WORLD["agents"]["hauler-mistral"])
        self._saved_station = copy.deepcopy(WORLD["agents"]["station"])

        # Clean slate
        WORLD["station_upgrades"] = {}
        WORLD["station_resources"] = {"water": 0, "gas": 0, "parts": []}
        WORLD["structures"] = []
        WORLD["stones"] = []
        WORLD["ground_items"] = []
        WORLD["delivered_items"] = []
        WORLD["storm"] = storm_mod.make_storm_state()

        # Reset rover
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        rover["battery"] = 1.0
        rover["inventory"] = []
        rover["memory"] = []

        # Reset hauler
        hauler = WORLD["agents"]["hauler-mistral"]
        hauler["position"] = [5, 5]
        hauler["battery"] = 1.0
        hauler["inventory"] = []
        hauler["memory"] = []

        # Reset station position
        WORLD["agents"]["station"]["position"] = [0, 0]

        _ensure_stone_index()

    def tearDown(self):
        WORLD["agents"]["rover-mistral"] = self._saved_rover
        WORLD["agents"]["hauler-mistral"] = self._saved_hauler
        WORLD["agents"]["station"] = self._saved_station

        for key, val in self._saved_world.items():
            WORLD[key] = val

        _ensure_stone_index()


# ── US1: Core action tests ───────────────────────────────────────────────────────


class TestCollectGas(_WorldSaveRestore):
    """Tests for _execute_collect_gas via execute_action."""

    def test_collect_gas_success(self):
        """Rover adjacent to gas plant with stored gas collects successfully."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=30)]

        result = execute_action("rover-mistral", "collect_gas", {})

        self.assertTrue(result["ok"])
        self.assertEqual(result["gas_collected"], 30)
        self.assertEqual(result["source"], [5, 6])
        self.assertEqual(len(rover["inventory"]), 1)
        self.assertEqual(rover["inventory"][0]["type"], "gas")
        self.assertEqual(rover["inventory"][0]["quantity"], 30)
        # Gas plant should be emptied
        self.assertEqual(WORLD["structures"][0]["contents"]["gas_stored"], 0)

    def test_collect_gas_battery_deducted(self):
        """Battery cost is deducted on successful collection."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        before = rover["battery"]
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=10)]

        execute_action("rover-mistral", "collect_gas", {})

        self.assertAlmostEqual(rover["battery"], before - BATTERY_COST_COLLECT_GAS)

    def test_collect_gas_no_adjacent_plant(self):
        """Fails when no gas plant is adjacent."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        WORLD["structures"] = [_make_gas_plant(pos=[10, 10], gas_stored=50)]

        result = execute_action("rover-mistral", "collect_gas", {})

        self.assertFalse(result["ok"])
        self.assertIn("no adjacent", result["error"].lower())

    def test_collect_gas_plant_empty(self):
        """Fails when gas plant has no stored gas."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=0)]

        result = execute_action("rover-mistral", "collect_gas", {})

        self.assertFalse(result["ok"])
        self.assertIn("no stored gas", result["error"].lower())

    def test_collect_gas_insufficient_battery(self):
        """Fails when rover has insufficient battery."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        rover["battery"] = 0.0
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=50)]

        result = execute_action("rover-mistral", "collect_gas", {})

        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())

    def test_collect_gas_inactive_plant_ignored(self):
        """Inactive gas plant is not considered adjacent."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=50, active=False)]

        result = execute_action("rover-mistral", "collect_gas", {})

        self.assertFalse(result["ok"])
        self.assertIn("no adjacent", result["error"].lower())

    def test_collect_gas_drone_blocked(self):
        """Drones cannot collect gas."""
        result = execute_action("drone-mistral", "collect_gas", {})
        self.assertFalse(result["ok"])
        self.assertIn("drone", result["error"].lower())

    def test_collect_gas_hauler_blocked(self):
        """Haulers cannot collect gas."""
        result = execute_action("hauler-mistral", "collect_gas", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())


class TestStationRecallAgent(unittest.TestCase):
    """Tests for station recall_agent action."""

    def test_recall_agent_success(self):
        """Station recall_agent returns ok with agent_id and reason."""
        result = station_execute_action(
            {
                "name": "recall_agent",
                "params": {"agent_id": "rover-mistral", "reason": "Low battery"},
            }
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "rover-mistral")
        self.assertEqual(result["reason"], "Low battery")

    def test_recall_agent_default_reason(self):
        """recall_agent uses default reason when none provided."""
        result = station_execute_action(
            {"name": "recall_agent", "params": {"agent_id": "rover-mistral"}}
        )
        self.assertTrue(result["ok"])
        self.assertIn("recall", result["reason"].lower())

    def test_recall_agent_hauler(self):
        """Station can recall a hauler."""
        result = station_execute_action(
            {
                "name": "recall_agent",
                "params": {"agent_id": "hauler-mistral", "reason": "Storm incoming"},
            }
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "hauler-mistral")

    def test_station_unknown_action(self):
        """Unknown station action returns error."""
        result = station_execute_action({"name": "fly_to_mars", "params": {}})
        self.assertFalse(result["ok"])
        self.assertIn("unknown", result["error"].lower())


class TestUpgradeBaseEdgeCases(_WorldSaveRestore):
    """Tests for _execute_upgrade_base edge cases."""

    def test_upgrade_base_wrong_position(self):
        """Upgrade fails when rover is not at station."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [10, 10]  # Station is at [0, 0]
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}

        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "charge_mk2"})

        self.assertFalse(result["ok"])
        self.assertIn("station", result["error"].lower())

    def test_upgrade_base_max_level(self):
        """Upgrade fails when already at max level."""
        rover = WORLD["agents"]["rover-mistral"]
        station = WORLD["agents"]["station"]
        rover["position"] = list(station["position"])
        WORLD["station_resources"] = {"water": 1000, "gas": 1000, "parts": []}
        # Set charge_mk2 to its max_level (1)
        WORLD["station_upgrades"] = {"charge_mk2": 1}

        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "charge_mk2"})

        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())

    def test_upgrade_base_unknown_upgrade(self):
        """Upgrade fails for unknown upgrade name."""
        rover = WORLD["agents"]["rover-mistral"]
        station = WORLD["agents"]["station"]
        rover["position"] = list(station["position"])
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}

        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "warp_drive"})

        self.assertFalse(result["ok"])
        self.assertIn("unknown upgrade", result["error"].lower())

    def test_upgrade_base_insufficient_water(self):
        """Upgrade fails when not enough water."""
        rover = WORLD["agents"]["rover-mistral"]
        station = WORLD["agents"]["station"]
        rover["position"] = list(station["position"])
        WORLD["station_resources"] = {"water": 0, "gas": 1000, "parts": []}

        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "charge_mk2"})

        self.assertFalse(result["ok"])
        self.assertIn("water", result["error"].lower())

    def test_upgrade_base_insufficient_gas(self):
        """Upgrade fails when not enough gas."""
        rover = WORLD["agents"]["rover-mistral"]
        station = WORLD["agents"]["station"]
        rover["position"] = list(station["position"])
        WORLD["station_resources"] = {"water": 1000, "gas": 0, "parts": []}

        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "charge_mk2"})

        self.assertFalse(result["ok"])
        self.assertIn("gas", result["error"].lower())

    def test_upgrade_base_all_types_succeed(self):
        """Each upgrade type succeeds with sufficient resources."""
        rover = WORLD["agents"]["rover-mistral"]
        station = WORLD["agents"]["station"]
        rover["position"] = list(station["position"])

        for upgrade_name, cfg in UPGRADES.items():
            WORLD["station_upgrades"] = {}
            WORLD["station_resources"] = {"water": 1000, "gas": 1000, "parts": []}

            result = execute_action("rover-mistral", "upgrade_base", {"upgrade": upgrade_name})

            self.assertTrue(result["ok"], f"Upgrade {upgrade_name} should succeed")
            self.assertEqual(result["upgrade"], upgrade_name)
            self.assertEqual(result["new_level"], 1)
            self.assertEqual(result["cost"]["water"], int(cfg.get("water", 0)))
            self.assertEqual(result["cost"]["gas"], int(cfg.get("gas", 0)))

    def test_upgrade_base_deducts_resources(self):
        """Upgrade deducts correct water and gas from station_resources."""
        rover = WORLD["agents"]["rover-mistral"]
        station = WORLD["agents"]["station"]
        rover["position"] = list(station["position"])
        WORLD["station_resources"] = {"water": 200, "gas": 100, "parts": []}

        cfg = UPGRADES["charge_mk2"]
        execute_action("rover-mistral", "upgrade_base", {"upgrade": "charge_mk2"})

        self.assertEqual(WORLD["station_resources"]["water"], 200 - int(cfg["water"]))
        self.assertEqual(WORLD["station_resources"]["gas"], 100 - int(cfg["gas"]))

    def test_upgrade_base_drone_blocked(self):
        """Drones cannot upgrade base."""
        result = execute_action("drone-mistral", "upgrade_base", {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("drone", result["error"].lower())

    def test_upgrade_base_hauler_blocked(self):
        """Haulers cannot upgrade base."""
        result = execute_action("hauler-mistral", "upgrade_base", {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())


# ── US2: Agent loop tests ────────────────────────────────────────────────────────


class TestHaulerLoopTick(unittest.IsolatedAsyncioTestCase):
    """Tests for HaulerLoop.tick() with mocked reasoner and broadcaster."""

    def setUp(self):
        self._saved_hauler = copy.deepcopy(WORLD["agents"]["hauler-mistral"])
        self._saved_station = copy.deepcopy(WORLD["agents"]["station"])
        self._saved_storm = copy.deepcopy(WORLD.get("storm", storm_mod.make_storm_state()))

        hauler = WORLD["agents"]["hauler-mistral"]
        hauler["position"] = [5, 5]
        hauler["battery"] = 1.0
        hauler["inventory"] = []
        hauler["memory"] = []
        hauler["goal_confidence"] = 0.5

        WORLD["storm"] = storm_mod.make_storm_state()
        WORLD["mission"] = {
            "status": "running",
            "target_type": "basalt_vein",
            "target_quantity": 300,
            "collected_quantity": 0,
            "water_collected": 0,
            "gas_collected": 0,
        }

    def tearDown(self):
        WORLD["agents"]["hauler-mistral"] = self._saved_hauler
        WORLD["agents"]["station"] = self._saved_station
        WORLD["storm"] = self._saved_storm

    @patch("app.agent.broadcaster")
    async def test_tick_executes_move_action(self, mock_broadcaster):
        """HaulerLoop tick executes a move action from the reasoner."""
        from app.agent import HaulerLoop

        mock_broadcaster.send = AsyncMock()

        loop = HaulerLoop(agent_id="hauler-mistral", interval=1.0)
        # Mock the reasoner to return a move action
        mock_turn = {
            "thinking": "I should move north to explore.",
            "action": {"name": "move", "params": {"direction": "north"}},
        }
        loop._reasoner = MagicMock()
        loop._reasoner.run_turn = MagicMock(return_value=mock_turn)

        host = MagicMock()
        host.drain_inbox = MagicMock(return_value=[])
        host.broadcast = AsyncMock()

        await loop.tick(host)

        # Verify action was executed (hauler moved north)
        hauler = WORLD["agents"]["hauler-mistral"]
        self.assertEqual(hauler["position"], [5, 6])
        # Verify broadcast was called
        self.assertTrue(host.broadcast.called)

    @patch("app.agent.broadcaster")
    async def test_tick_broadcasts_thinking_and_action(self, mock_broadcaster):
        """Tick broadcasts thinking event and action event."""
        from app.agent import HaulerLoop

        mock_broadcaster.send = AsyncMock()

        loop = HaulerLoop(agent_id="hauler-mistral", interval=1.0)
        mock_turn = {
            "thinking": "Moving north.",
            "action": {"name": "move", "params": {"direction": "north"}},
        }
        loop._reasoner = MagicMock()
        loop._reasoner.run_turn = MagicMock(return_value=mock_turn)

        host = MagicMock()
        host.drain_inbox = MagicMock(return_value=[])
        host.broadcast = AsyncMock()

        await loop.tick(host)

        # Should have at least 2 broadcast calls: thinking + action
        broadcast_calls = host.broadcast.call_args_list
        payloads = [call[0][0] for call in broadcast_calls]

        event_names = [p.get("name") for p in payloads if isinstance(p, dict)]
        self.assertIn("thinking", event_names)
        self.assertIn("move", event_names)

    @patch("app.agent.broadcaster")
    async def test_tick_updates_goal_confidence(self, mock_broadcaster):
        """Goal confidence increases after successful action."""
        from app.agent import HaulerLoop

        mock_broadcaster.send = AsyncMock()

        hauler = WORLD["agents"]["hauler-mistral"]
        before_conf = hauler["goal_confidence"]

        loop = HaulerLoop(agent_id="hauler-mistral", interval=1.0)
        mock_turn = {
            "thinking": "Moving.",
            "action": {"name": "move", "params": {"direction": "north"}},
        }
        loop._reasoner = MagicMock()
        loop._reasoner.run_turn = MagicMock(return_value=mock_turn)

        host = MagicMock()
        host.drain_inbox = MagicMock(return_value=[])
        host.broadcast = AsyncMock()

        await loop.tick(host)

        after_conf = hauler["goal_confidence"]
        self.assertGreater(after_conf, before_conf)

    @patch("app.agent.broadcaster")
    async def test_tick_auto_charges_at_station(self, mock_broadcaster):
        """Hauler is auto-charged when at station with low battery."""
        from app.agent import HaulerLoop

        mock_broadcaster.send = AsyncMock()

        station_pos = WORLD["agents"]["station"]["position"]
        hauler = WORLD["agents"]["hauler-mistral"]
        hauler["position"] = list(station_pos)
        hauler["battery"] = 0.5

        loop = HaulerLoop(agent_id="hauler-mistral", interval=1.0)
        mock_turn = {
            "thinking": "Waiting at station.",
            "action": None,
        }
        loop._reasoner = MagicMock()
        loop._reasoner.run_turn = MagicMock(return_value=mock_turn)

        host = MagicMock()
        host.drain_inbox = MagicMock(return_value=[])
        host.broadcast = AsyncMock()

        await loop.tick(host)

        # Battery should have increased due to auto-charge
        self.assertGreater(hauler["battery"], 0.5)


# ── US3: Integration tests ───────────────────────────────────────────────────────


class TestResourceLifecycle(_WorldSaveRestore):
    """End-to-end: dig -> drop -> pickup -> unload -> delivered."""

    def test_full_dig_drop_pickup_unload_chain(self):
        """Complete resource chain from vein to delivered_items."""
        rover = WORLD["agents"]["rover-mistral"]
        hauler = WORLD["agents"]["hauler-mistral"]
        station_pos = WORLD["agents"]["station"]["position"]

        # Step 1: Place an analyzed stone at rover position and dig it
        _place_analyzed_stone(5, 5, grade="high", quantity=200)
        dig_result = execute_action("rover-mistral", "dig", {})
        self.assertTrue(dig_result["ok"])
        self.assertEqual(len(rover["inventory"]), 1)
        self.assertEqual(rover["inventory"][0]["type"], "basalt_vein")

        # Step 2: Rover drops the item
        drop_result = execute_action("rover-mistral", "drop_item", {"index": 0})
        self.assertTrue(drop_result["ok"])
        self.assertEqual(len(rover["inventory"]), 0)
        self.assertEqual(len(WORLD["ground_items"]), 1)
        self.assertEqual(WORLD["ground_items"][0]["type"], "basalt_vein")

        # Step 3: Hauler picks up the dropped item
        hauler["position"] = [5, 5]  # Same position as drop
        pickup_result = execute_action("hauler-mistral", "pickup_cargo", {})
        self.assertTrue(pickup_result["ok"])
        self.assertEqual(len(hauler["inventory"]), 1)
        self.assertEqual(hauler["inventory"][0]["type"], "basalt_vein")

        # Step 4: Hauler moves to station and unloads
        hauler["position"] = list(station_pos)
        unload_result = execute_action("hauler-mistral", "unload_cargo", {})
        self.assertTrue(unload_result["ok"])
        self.assertEqual(len(hauler["inventory"]), 0)
        self.assertGreater(len(WORLD["delivered_items"]), 0)
        self.assertEqual(WORLD["delivered_items"][-1]["type"], "basalt_vein")

    def test_dig_requires_analyzed_stone(self):
        """Dig fails on unanalyzed stone."""
        _place_unanalyzed_stone(5, 5)

        result = execute_action("rover-mistral", "dig", {})

        self.assertFalse(result["ok"])
        self.assertIn("not yet analyzed", result["error"].lower())

    def test_analyze_then_dig_chain(self):
        """Analyze followed by dig completes successfully."""
        rover = WORLD["agents"]["rover-mistral"]
        _place_unanalyzed_stone(5, 5, grade="rich", quantity=500)

        analyze_result = execute_action("rover-mistral", "analyze", {})
        self.assertTrue(analyze_result["ok"])
        self.assertEqual(analyze_result["stone"]["grade"], "rich")

        dig_result = execute_action("rover-mistral", "dig", {})
        self.assertTrue(dig_result["ok"])
        self.assertEqual(dig_result["stone"]["quantity"], 500)
        self.assertEqual(len(rover["inventory"]), 1)


class TestStormBatteryEffects(_WorldSaveRestore):
    """Tests for storm battery cost multiplier on various actions."""

    def _activate_storm(self, intensity=0.5):
        """Put the world into an active storm with given intensity."""
        WORLD["storm"] = {
            "phase": "active",
            "next_storm_tick": 0,
            "active_start": 0,
            "active_end": 9999,
            "intensity": intensity,
            "warning_start": 0,
        }

    def test_storm_clear_multiplier_is_one(self):
        """In clear weather, battery multiplier is 1.0."""
        WORLD["storm"] = storm_mod.make_storm_state()
        mult = storm_mod.get_battery_multiplier(WORLD)
        self.assertEqual(mult, 1.0)

    def test_storm_active_multiplier_increases(self):
        """Active storm increases battery multiplier above 1.0."""
        self._activate_storm(intensity=0.5)
        mult = storm_mod.get_battery_multiplier(WORLD)
        self.assertGreater(mult, 1.0)

    def test_storm_move_costs_more_battery(self):
        """Moving during a storm costs more battery than in clear weather."""
        rover = WORLD["agents"]["rover-mistral"]

        # Use origin area (guaranteed obstacle-free)
        rover["position"] = [0, 0]
        rover["battery"] = 1.0
        WORLD["storm"] = storm_mod.make_storm_state()  # clear weather
        result_clear = execute_action("rover-mistral", "move", {"direction": "east"})
        clear_cost = 1.0 - rover["battery"]
        self.assertTrue(result_clear.get("ok", False), f"Clear move failed: {result_clear}")

        # Reset position for storm move
        rover["position"] = [0, 0]
        rover["battery"] = 1.0
        self._activate_storm(intensity=0.6)
        result_storm = execute_action("rover-mistral", "move", {"direction": "east"})
        storm_cost = 1.0 - rover["battery"]
        self.assertTrue(result_storm.get("ok", False), f"Storm move failed: {result_storm}")

        self.assertGreater(storm_cost, clear_cost)

    def test_storm_collect_gas_costs_more(self):
        """Collecting gas during a storm costs more battery."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]

        # Measure clear-weather cost
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=50)]
        rover["battery"] = 1.0
        execute_action("rover-mistral", "collect_gas", {})
        clear_cost = 1.0 - rover["battery"]

        # Reset and measure storm cost
        WORLD["structures"] = [_make_gas_plant(pos=[5, 6], gas_stored=50)]
        rover["battery"] = 1.0
        rover["inventory"] = []
        self._activate_storm(intensity=0.8)
        execute_action("rover-mistral", "collect_gas", {})
        storm_cost = 1.0 - rover["battery"]

        self.assertGreater(storm_cost, clear_cost)

    def test_storm_max_intensity_multiplier(self):
        """Full intensity storm produces maximum battery multiplier."""
        self._activate_storm(intensity=1.0)
        mult = storm_mod.get_battery_multiplier(WORLD)
        self.assertAlmostEqual(mult, storm_mod.STORM_MAX_BATTERY_MULT)

    def test_storm_lifecycle_phases(self):
        """Storm progresses through clear -> warning -> active -> clear."""
        WORLD["tick"] = 0
        WORLD["storm"] = {
            "phase": "clear",
            "next_storm_tick": 2,
            "active_start": 0,
            "active_end": 0,
            "intensity": 0.0,
            "warning_start": 0,
        }

        # Before storm tick -- still clear
        WORLD["tick"] = 1
        events = storm_mod.check_storm_tick(WORLD)
        self.assertEqual(WORLD["storm"]["phase"], "clear")

        # At next_storm_tick -- transitions to warning
        WORLD["tick"] = 2
        events = storm_mod.check_storm_tick(WORLD)
        self.assertEqual(WORLD["storm"]["phase"], "warning")
        self.assertTrue(any("storm_warning" in str(e.get("name", "")) for e in events))

        # At active_start -- transitions to active
        active_start = WORLD["storm"]["active_start"]
        WORLD["tick"] = active_start
        events = storm_mod.check_storm_tick(WORLD)
        self.assertEqual(WORLD["storm"]["phase"], "active")

        # At active_end -- transitions back to clear
        active_end = WORLD["storm"]["active_end"]
        WORLD["tick"] = active_end
        events = storm_mod.check_storm_tick(WORLD)
        self.assertEqual(WORLD["storm"]["phase"], "clear")


if __name__ == "__main__":
    unittest.main()
