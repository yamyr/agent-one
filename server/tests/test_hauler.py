"""Tests for the Hauler agent: movement, cargo operations, and task planning."""

import unittest

from app.world import (
    world,
    execute_action,
    WORLD,
    BATTERY_COST_MOVE_HAULER,
    MAX_INVENTORY_HAULER,
    MAX_MOVE_DISTANCE_HAULER,
)


def _reset_hauler(pos=None, battery=1.0):
    """Reset hauler-1 to a known state for testing."""
    agent = world.state["agents"]["hauler-1"]
    agent["position"] = list(pos) if pos else [5, 5]
    agent["battery"] = battery
    agent["inventory"] = []
    agent["memory"] = []
    return agent


def _reset_rover(agent_id="rover-mistral", pos=None, battery=1.0):
    """Reset a rover to a known state."""
    agent = world.state["agents"][agent_id]
    agent["position"] = list(pos) if pos else [5, 5]
    agent["battery"] = battery
    agent["inventory"] = []
    agent["memory"] = []
    return agent


class TestHaulerMove(unittest.TestCase):
    """Test hauler movement via execute_action."""

    def setUp(self):
        # re-init hauler state
        WORLD["structures"] = []
        _reset_hauler()

    def test_move_north(self):
        result = execute_action("hauler-1", "move", {"direction": "north"})
        self.assertTrue(result["ok"])
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(agent["position"], [5, 4])

    def test_move_south(self):
        result = execute_action("hauler-1", "move", {"direction": "south"})
        self.assertTrue(result["ok"])
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(agent["position"], [5, 6])

    def test_move_east(self):
        result = execute_action("hauler-1", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(agent["position"], [6, 5])

    def test_move_west(self):
        result = execute_action("hauler-1", "move", {"direction": "west"})
        self.assertTrue(result["ok"])
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(agent["position"], [4, 5])

    def test_move_drains_battery(self):
        agent = _reset_hauler(battery=1.0)
        execute_action("hauler-1", "move", {"direction": "north"})
        expected = 1.0 - BATTERY_COST_MOVE_HAULER
        self.assertAlmostEqual(agent["battery"], expected, places=6)

    def test_move_max_distance(self):
        result = execute_action(
            "hauler-1",
            "move",
            {"direction": "east", "distance": MAX_MOVE_DISTANCE_HAULER},
        )
        self.assertTrue(result["ok"])
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(agent["position"], [5 + MAX_MOVE_DISTANCE_HAULER, 5])

    def test_move_insufficient_battery(self):
        _reset_hauler(battery=0.0)
        result = execute_action("hauler-1", "move", {"direction": "north"})
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())

    def test_move_invalid_direction(self):
        result = execute_action("hauler-1", "move", {"direction": "diagonal"})
        self.assertFalse(result["ok"])


class TestHaulerRestrictedActions(unittest.TestCase):
    """Verify haulers cannot perform rover/drone-only actions."""

    def setUp(self):
        # re-init hauler state
        WORLD["structures"] = []
        _reset_hauler()

    def test_cannot_analyze(self):
        result = execute_action("hauler-1", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_dig(self):
        result = execute_action("hauler-1", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_gather_ice(self):
        result = execute_action("hauler-1", "gather_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_recycle_ice(self):
        result = execute_action("hauler-1", "recycle_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_build_gas_plant(self):
        result = execute_action("hauler-1", "build_gas_plant", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_collect_gas(self):
        result = execute_action("hauler-1", "collect_gas", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_upgrade_base(self):
        result = execute_action("hauler-1", "upgrade_base", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_scan(self):
        result = execute_action("hauler-1", "scan", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_deploy_solar_panel(self):
        result = execute_action("hauler-1", "deploy_solar_panel", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_use_solar_battery(self):
        result = execute_action("hauler-1", "use_solar_battery", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_drop_item(self):
        result = execute_action("hauler-1", "drop_item", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_investigate_structure(self):
        result = execute_action("hauler-1", "investigate_structure", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_use_refinery(self):
        result = execute_action("hauler-1", "use_refinery", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_cannot_upgrade_building(self):
        result = execute_action("hauler-1", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_rover_cannot_pickup_cargo(self):
        result = execute_action("rover-mistral", "pickup_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_rover_cannot_load_cargo(self):
        result = execute_action("rover-mistral", "load_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_rover_cannot_unload_cargo(self):
        result = execute_action("rover-mistral", "unload_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())


class TestPickupCargo(unittest.TestCase):
    """Test hauler pickup_cargo action from ground items."""

    def setUp(self):
        # re-init hauler state
        WORLD["structures"] = []
        _reset_hauler()
        WORLD["ground_items"] = []

    def test_pickup_success(self):
        WORLD["ground_items"] = [
            {"position": [5, 5], "type": "basalt", "quantity": 10},
        ]
        result = execute_action("hauler-1", "pickup_cargo", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["picked_up_count"], 1)
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(len(agent["inventory"]), 1)
        self.assertEqual(agent["inventory"][0]["type"], "basalt")

    def test_pickup_no_items(self):
        result = execute_action("hauler-1", "pickup_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("no cargo", result["error"].lower())

    def test_pickup_wrong_position(self):
        WORLD["ground_items"] = [
            {"position": [10, 10], "type": "basalt", "quantity": 10},
        ]
        result = execute_action("hauler-1", "pickup_cargo", {})
        self.assertFalse(result["ok"])

    def test_pickup_multiple_items(self):
        WORLD["ground_items"] = [
            {"position": [5, 5], "type": "basalt", "quantity": 5},
            {"position": [5, 5], "type": "core", "quantity": 3},
        ]
        result = execute_action("hauler-1", "pickup_cargo", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["picked_up_count"], 2)
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(len(agent["inventory"]), 2)

    def test_pickup_inventory_full(self):
        agent = WORLD["agents"]["hauler-1"]
        agent["inventory"] = [{"type": "basalt", "quantity": 1}] * MAX_INVENTORY_HAULER
        WORLD["ground_items"] = [
            {"position": [5, 5], "type": "core", "quantity": 10},
        ]
        result = execute_action("hauler-1", "pickup_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("full", result["error"].lower())

    def test_pickup_low_battery(self):
        _reset_hauler(battery=0.0)
        WORLD["ground_items"] = [
            {"position": [5, 5], "type": "basalt", "quantity": 10},
        ]
        result = execute_action("hauler-1", "pickup_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())


class TestLoadCargo(unittest.TestCase):
    """Test hauler load/load_cargo from cargo drops."""

    def setUp(self):
        # re-init hauler state
        WORLD["structures"] = []
        _reset_hauler()
        WORLD["cargo_drops"] = []

    def test_load_success(self):
        WORLD["cargo_drops"] = [
            {
                "position": [5, 5],
                "items": [{"type": "basalt", "quantity": 10}],
            }
        ]
        result = execute_action("hauler-1", "load", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["loaded_count"], 1)
        agent = WORLD["agents"]["hauler-1"]
        self.assertEqual(len(agent["inventory"]), 1)

    def test_load_cargo_alias(self):
        WORLD["cargo_drops"] = [
            {
                "position": [5, 5],
                "items": [{"type": "core", "quantity": 5}],
            }
        ]
        result = execute_action("hauler-1", "load_cargo", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["loaded_count"], 1)

    def test_load_no_cargo_drop(self):
        result = execute_action("hauler-1", "load", {})
        self.assertFalse(result["ok"])
        self.assertIn("no cargo", result["error"].lower())

    def test_load_inventory_full(self):
        agent = WORLD["agents"]["hauler-1"]
        agent["inventory"] = [{"type": "basalt", "quantity": 1}] * MAX_INVENTORY_HAULER
        WORLD["cargo_drops"] = [
            {
                "position": [5, 5],
                "items": [{"type": "core", "quantity": 10}],
            }
        ]
        result = execute_action("hauler-1", "load", {})
        self.assertFalse(result["ok"])
        self.assertIn("full", result["error"].lower())

    def test_load_low_battery(self):
        _reset_hauler(battery=0.0)
        WORLD["cargo_drops"] = [
            {
                "position": [5, 5],
                "items": [{"type": "basalt", "quantity": 10}],
            }
        ]
        result = execute_action("hauler-1", "load", {})
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())


class TestUnloadCargo(unittest.TestCase):
    """Test hauler unload/unload_cargo action."""

    def setUp(self):
        # re-init hauler state
        WORLD["structures"] = []
        WORLD["delivered_items"] = []
        WORLD["cargo_drops"] = []

    def test_unload_at_station(self):
        station_pos = WORLD["agents"]["station"]["position"]
        agent = _reset_hauler(pos=station_pos, battery=1.0)
        agent["inventory"] = [{"type": "basalt", "quantity": 10}]
        result = execute_action("hauler-1", "unload", {})
        self.assertTrue(result["ok"])
        self.assertEqual(len(agent["inventory"]), 0)
        self.assertGreater(len(WORLD["delivered_items"]), 0)

    def test_unload_cargo_alias(self):
        station_pos = WORLD["agents"]["station"]["position"]
        agent = _reset_hauler(pos=station_pos, battery=1.0)
        agent["inventory"] = [{"type": "core", "quantity": 5}]
        result = execute_action("hauler-1", "unload_cargo", {})
        self.assertTrue(result["ok"])

    def test_unload_not_at_station(self):
        agent = _reset_hauler(pos=[5, 5], battery=1.0)
        agent["inventory"] = [{"type": "basalt", "quantity": 10}]
        result = execute_action("hauler-1", "unload", {})
        self.assertTrue(result["ok"])
        # Items should go to cargo_drops, not delivered_items
        self.assertEqual(len(WORLD.get("delivered_items", [])), 0)

    def test_unload_empty_inventory(self):
        _reset_hauler(pos=[0, 0], battery=1.0)
        result = execute_action("hauler-1", "unload", {})
        self.assertFalse(result["ok"])
        self.assertIn("no cargo", result["error"].lower())

    def test_unload_low_battery(self):
        agent = _reset_hauler(pos=[0, 0], battery=0.0)
        agent["inventory"] = [{"type": "basalt", "quantity": 10}]
        result = execute_action("hauler-1", "unload", {})
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())


class TestLegacyCargoActions(unittest.TestCase):
    """Verify legacy cargo transfer actions are disabled."""

    def setUp(self):
        # re-init hauler state
        WORLD["structures"] = []
        _reset_hauler()

    def test_load_from_rover_disabled(self):
        result = execute_action("hauler-1", "load_from_rover", {})
        self.assertFalse(result["ok"])
        self.assertIn("legacy", result["error"].lower())

    def test_unload_at_station_legacy_disabled(self):
        result = execute_action("hauler-1", "unload_at_station", {})
        self.assertFalse(result["ok"])
        self.assertIn("legacy", result["error"].lower())

    def test_pick_up_from_disabled(self):
        result = execute_action("hauler-1", "pick_up_from", {})
        self.assertFalse(result["ok"])
        self.assertIn("legacy", result["error"].lower())

    def test_transfer_cargo_disabled(self):
        result = execute_action("hauler-1", "transfer_cargo", {})
        self.assertFalse(result["ok"])
        self.assertIn("legacy", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
