import unittest

from app.world import (
    BATTERY_COST_UPGRADE,
    MAX_UPGRADE_LEVEL,
    UPGRADE_BASALT_COST,
    STRUCTURE_TYPES,
    execute_action,
    world,
)


def _make_structure(stype="solar_panel_structure", pos=(5, 6), active=True, upgrade_level=1):
    contents = {}
    for template in STRUCTURE_TYPES:
        if template["type"] == stype:
            contents = dict(template["contents"])
            break
    return {
        "type": stype,
        "category": "building",
        "position": list(pos),
        "explored": True,
        "active": active,
        "upgrade_level": upgrade_level,
        "description": f"Test {stype}",
        "contents": contents,
    }


class TestBuildingUpgrades(unittest.TestCase):
    def setUp(self):
        rover = world.state["agents"]["rover-mistral"]
        self._orig_position = list(rover["position"])
        self._orig_battery = rover["battery"]
        self._orig_inventory = list(rover.get("inventory", []))
        self._orig_structures = world.state.get("structures", [])[:]

        rover["position"] = [5, 5]
        rover["battery"] = 1.0
        rover["inventory"] = [
            {"type": "basalt_vein", "grade": "low", "quantity": 25},
            {"type": "ice", "grade": "thin", "quantity": 5},
        ]
        world.state["structures"] = [_make_structure()]

    def tearDown(self):
        rover = world.state["agents"]["rover-mistral"]
        rover["position"] = self._orig_position
        rover["battery"] = self._orig_battery
        rover["inventory"] = self._orig_inventory
        world.state["structures"] = self._orig_structures

    def test_upgrade_increases_level(self):
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["new_level"], 2)
        self.assertEqual(world.state["structures"][0]["upgrade_level"], 2)

    def test_max_upgrade_level_enforced(self):
        world.state["structures"] = [_make_structure(upgrade_level=MAX_UPGRADE_LEVEL)]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())

    def test_basalt_consumed_on_upgrade(self):
        before = len(
            [
                i
                for i in world.state["agents"]["rover-mistral"]["inventory"]
                if i.get("type") == "basalt_vein"
            ]
        )
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertTrue(result["ok"])
        after = len(
            [
                i
                for i in world.state["agents"]["rover-mistral"]["inventory"]
                if i.get("type") == "basalt_vein"
            ]
        )
        self.assertEqual(before - after, UPGRADE_BASALT_COST)

    def test_battery_cost_on_upgrade(self):
        before = world.state["agents"]["rover-mistral"]["battery"]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertTrue(result["ok"])
        after = world.state["agents"]["rover-mistral"]["battery"]
        self.assertAlmostEqual(before - after, BATTERY_COST_UPGRADE, places=6)

    def test_upgrade_bonuses_applied(self):
        structure = world.state["structures"][0]
        base_rate = structure["contents"]["charge_rate"]
        base_radius = structure["contents"]["charge_radius"]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertTrue(result["ok"])
        updated = world.state["structures"][0]
        self.assertAlmostEqual(
            updated["contents"]["charge_rate"], round(base_rate * 1.5, 5), places=5
        )
        self.assertEqual(updated["contents"]["charge_radius"], base_radius + 1)

    def test_upgrade_fails_with_insufficient_basalt(self):
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "ice", "grade": "thin", "quantity": 5}
        ]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("need", result["error"].lower())
        self.assertIn("basalt", result["error"].lower())

    def test_upgrade_fails_for_non_adjacent_structure(self):
        world.state["structures"] = [_make_structure(pos=(8, 8), active=True)]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("within reach", result["error"].lower())

    def test_upgrade_fails_for_inactive_structure(self):
        world.state["structures"] = [_make_structure(active=False)]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("active structure", result["error"].lower())
