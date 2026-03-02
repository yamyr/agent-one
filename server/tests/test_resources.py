import copy
import unittest

from app.world import (
    BATTERY_COST_BUILD_GAS_PLANT,
    BATTERY_COST_GATHER_ICE,
    BATTERY_COST_PROCESS_ICE,
    ICE_TO_WATER_RATIO,
    UPGRADES,
    WORLD,
    _ensure_stone_index,
    _execute_build_gas_plant,
    _execute_upgrade_base,
    _stone_index,
    execute_action,
    update_gas_plants,
)


def _place_ice_stone(x, y):
    stone = {
        "position": [x, y],
        "type": "ice",
        "grade": "n/a",
        "quantity": 1,
        "analyzed": True,
    }
    _ensure_stone_index()
    WORLD.setdefault("stones", []).append(stone)
    _stone_index[(x, y)] = stone
    return stone


class _ResourceTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_world_parts = {
            "station_upgrades": copy.deepcopy(WORLD.get("station_upgrades", {})),
            "station_resources": copy.deepcopy(
                WORLD.get("station_resources", {"water": 0, "gas": 0, "parts": []})
            ),
            "structures": copy.deepcopy(WORLD.get("structures", [])),
            "obstacles": copy.deepcopy(WORLD.get("obstacles", [])),
            "stones": copy.deepcopy(WORLD.get("stones", [])),
            "ice_deposits": copy.deepcopy(WORLD.get("ice_deposits", [])),
        }
        self._orig_rover = copy.deepcopy(WORLD["agents"]["rover-mistral"])
        self._orig_station = copy.deepcopy(WORLD["agents"]["station"])

        WORLD["station_upgrades"] = {}
        WORLD["station_resources"] = {"water": 0, "gas": 0, "parts": []}
        WORLD["structures"] = []
        WORLD["obstacles"] = []
        WORLD["stones"] = []
        WORLD["ice_deposits"] = []

        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        rover["battery"] = 1.0
        rover["inventory"] = []
        rover["memory"] = []

        WORLD["agents"]["station"]["position"] = [0, 0]
        _ensure_stone_index()

    def tearDown(self):
        WORLD["agents"]["rover-mistral"] = self._orig_rover
        WORLD["agents"]["station"] = self._orig_station

        WORLD["station_upgrades"] = self._orig_world_parts["station_upgrades"]
        WORLD["station_resources"] = self._orig_world_parts["station_resources"]
        WORLD["structures"] = self._orig_world_parts["structures"]
        WORLD["obstacles"] = self._orig_world_parts["obstacles"]
        WORLD["stones"] = self._orig_world_parts["stones"]
        WORLD["ice_deposits"] = self._orig_world_parts["ice_deposits"]
        _ensure_stone_index()


class TestGatherIce(_ResourceTestCase):
    def test_gather_ice_collects_stone_and_consumes_battery(self):
        rover = WORLD["agents"]["rover-mistral"]
        _place_ice_stone(5, 5)
        before = rover["battery"]

        result = execute_action("rover-mistral", "gather_ice", {})

        self.assertTrue(result["ok"])
        self.assertAlmostEqual(rover["battery"], before - BATTERY_COST_GATHER_ICE)
        self.assertIn({"type": "ice", "grade": "n/a", "quantity": 1}, rover["inventory"])
        self.assertEqual(WORLD["stones"], [])
        self.assertNotIn((5, 5), _stone_index)


class TestRecycleIce(_ResourceTestCase):
    def test_recycle_ice_uses_adjacent_active_water_processor(self):
        rover = WORLD["agents"]["rover-mistral"]
        rover["inventory"] = [{"type": "ice", "grade": "n/a", "quantity": 3}]
        WORLD["structures"] = [
            {
                "type": "water_processor",
                "position": [5, 6],
                "active": True,
                "explored": True,
            }
        ]
        before = rover["battery"]

        result = execute_action("rover-mistral", "recycle_ice", {})

        self.assertTrue(result["ok"])
        self.assertEqual(result["water_quantity"], 3 * ICE_TO_WATER_RATIO)
        self.assertAlmostEqual(rover["battery"], before - BATTERY_COST_PROCESS_ICE)
        self.assertEqual(
            rover["inventory"],
            [{"type": "water", "quantity": 3 * ICE_TO_WATER_RATIO}],
        )

    def test_recycle_ice_rejects_water_recycler_structure(self):
        rover = WORLD["agents"]["rover-mistral"]
        rover["inventory"] = [{"type": "ice", "grade": "n/a", "quantity": 1}]
        WORLD["structures"] = [
            {
                "type": "water_recycler",
                "position": [5, 6],
                "active": True,
                "explored": True,
            }
        ]

        result = execute_action("rover-mistral", "recycle_ice", {})

        self.assertFalse(result["ok"])
        self.assertIn("water processor", result["error"].lower())


class TestBuildGasPlant(_ResourceTestCase):
    def test_build_gas_plant_on_adjacent_geyser(self):
        rover = WORLD["agents"]["rover-mistral"]
        WORLD["station_resources"] = {"water": 10, "gas": 0, "parts": []}
        geyser = {
            "position": [5, 6],
            "kind": "geyser",
            "state": "idle",
            "gas_plant": None,
            "has_gas_plant": False,
        }
        WORLD["obstacles"] = [geyser]
        before = rover["battery"]

        result = _execute_build_gas_plant("rover-mistral", rover, {})

        self.assertTrue(result["ok"])
        self.assertAlmostEqual(rover["battery"], before - BATTERY_COST_BUILD_GAS_PLANT)
        self.assertIsNotNone(geyser["gas_plant"])
        self.assertTrue(geyser["has_gas_plant"])
        self.assertEqual(
            len([s for s in WORLD["structures"] if s.get("type") == "gas_plant"]),
            1,
        )
        self.assertEqual(WORLD["station_resources"]["water"], 5)


class TestUpgradeBase(_ResourceTestCase):
    def test_upgrade_base_uses_upgrades_dict_and_station_resources(self):
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        WORLD["station_upgrades"] = {}

        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["upgrade"], "charge_mk2")
        self.assertEqual(result["new_level"], 1)
        self.assertEqual(result["cost"], {"water": 50, "gas": 20})
        self.assertEqual(result["description"], UPGRADES["charge_mk2"]["description"])
        self.assertEqual(WORLD["station_upgrades"]["charge_mk2"], 1)
        self.assertEqual(WORLD["station_resources"]["water"], 50)
        self.assertEqual(WORLD["station_resources"]["gas"], 80)


class TestGasProduction(_ResourceTestCase):
    def test_update_gas_plants_returns_zero_without_active_plants(self):
        WORLD["structures"] = []
        self.assertEqual(update_gas_plants(), 0)


if __name__ == "__main__":
    unittest.main()
