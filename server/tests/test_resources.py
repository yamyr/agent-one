"""Tests for the resource system: ice gathering, water recycling, gas plants, and base upgrades."""

import unittest

from app.world import (
    world,
    execute_action,
    WORLD,
    UPGRADES,
    _execute_build_gas_plant,
    _execute_upgrade_base,
    _rebuild_stone_index,
)


def _reset_agent(agent_id="rover-mistral", pos=None, battery=1.0):
    """Reset an agent to a known state for testing."""
    agent = world.state["agents"][agent_id]
    agent["position"] = list(pos) if pos else [5, 5]
    agent["battery"] = battery
    agent["inventory"] = []
    agent["memory"] = []
    return agent


def _place_ice_stone(pos, quantity=1):
    """Place an ice-type stone in WORLD['stones'] at the given position."""
    stone = {
        "position": list(pos),
        "type": "ice",
        "grade": "n/a",
        "quantity": quantity,
        "analyzed": True,
    }
    WORLD.setdefault("stones", []).append(stone)
    _rebuild_stone_index()
    return stone


def _place_geyser(pos, state="idle"):
    """Place a test geyser obstacle at the given position."""
    geyser = {
        "position": list(pos),
        "kind": "geyser",
        "state": state,
        "_cycle_tick": 0,
        "gas_plant": None,
    }
    WORLD.setdefault("obstacles", []).append(geyser)
    return geyser


def _ensure_resources():
    """Ensure WORLD resource dicts exist."""
    WORLD.setdefault("resources", {"water": 0, "gas": 0})
    WORLD.setdefault("station_resources", {"water": 0, "gas": 0, "parts": []})


class TestGatherIce(unittest.TestCase):
    """Tests for the gather_ice action.

    _execute_gather_ice looks for stones with type='ice' in WORLD['stones']
    via _find_stone_at(). It removes the stone and adds an ice item to inventory.
    """

    def setUp(self):
        self.agent = _reset_agent(pos=[5, 5])
        self._orig_stones = list(WORLD.get("stones", []))
        _ensure_resources()

    def tearDown(self):
        WORLD["stones"] = self._orig_stones
        _rebuild_stone_index()

    def test_gather_ice_success(self):
        """Rover at an ice stone can gather ice."""
        _place_ice_stone([5, 5])
        result = execute_action("rover-mistral", "gather_ice", {})
        self.assertTrue(result["ok"])
        # Ice should be in inventory
        ice_items = [i for i in self.agent["inventory"] if i.get("type") == "ice"]
        self.assertEqual(len(ice_items), 1)
        # The stone should be removed from WORLD['stones']
        remaining = [s for s in WORLD["stones"] if s["position"] == [5, 5] and s["type"] == "ice"]
        self.assertEqual(len(remaining), 0)

    def test_gather_ice_no_deposit(self):
        """Rover with no ice stone at position fails."""
        result = execute_action("rover-mistral", "gather_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("No ice", result["error"])

    def test_gather_ice_low_battery(self):
        """Rover with low battery fails to gather."""
        _place_ice_stone([5, 5])
        self.agent["battery"] = 0.001
        result = execute_action("rover-mistral", "gather_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())

    def test_gather_ice_drone_forbidden(self):
        """Drones cannot gather ice."""
        result = execute_action("drone-mistral", "gather_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("Drones", result["error"])


class TestRecycleIce(unittest.TestCase):
    """Tests for the recycle_ice action.

    _execute_recycle_ice (via _execute_process_ice) requires an adjacent active
    water_recycler or water_processor structure. It pops ice from inventory,
    multiplies by conversion_rate, and adds water to inventory.
    """

    def setUp(self):
        # Place rover at [1,0] — adjacent to recycler but NOT at station [0,0]
        # This prevents check_mission_status from auto-delivering inventory
        self.agent = _reset_agent(pos=[1, 0])
        _ensure_resources()
        self._orig_station_pos = list(WORLD["agents"]["station"]["position"])
        WORLD["agents"]["station"]["position"] = [0, 0]
        # Save and replace structures to control water_recycler
        self._orig_structures = list(WORLD.get("structures", []))
        WORLD["structures"] = [
            s
            for s in WORLD.get("structures", [])
            if s.get("type") not in ("water_recycler", "water_processor")
        ]
        WORLD["structures"].append(
            {
                "type": "water_recycler",
                "position": [1, 0],
                "active": True,
                "explored": True,
                "contents": {"conversion_rate": 2},
            }
        )

    def tearDown(self):
        WORLD["agents"]["station"]["position"] = self._orig_station_pos
        WORLD["structures"] = self._orig_structures

    def test_recycle_ice_success(self):
        self.agent["inventory"] = [{"type": "ice", "quantity": 30}]
        result = execute_action("rover-mistral", "recycle_ice", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["water_quantity"], 60)  # 30 * conversion_rate(2) = 60
        # Ice should be removed from inventory, water added
        ice_items = [i for i in self.agent["inventory"] if i.get("type") == "ice"]
        self.assertEqual(len(ice_items), 0)
        water_items = [i for i in self.agent["inventory"] if i.get("type") == "water"]
        self.assertEqual(len(water_items), 1)
        self.assertEqual(water_items[0]["quantity"], 60)

    def test_recycle_ice_not_at_recycler(self):
        """Rover far from any recycler fails."""
        self.agent["position"] = [5, 5]
        self.agent["inventory"] = [{"type": "ice", "quantity": 30}]
        result = execute_action("rover-mistral", "recycle_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("recycler", result["error"].lower())

    def test_recycle_ice_no_ice(self):
        """Rover with no ice in inventory cannot recycle."""
        result = execute_action("rover-mistral", "recycle_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("ice", result["error"].lower())


class TestBuildGasPlant(unittest.TestCase):
    """Tests for the build_gas_plant action.

    The implementation stores gas_plant on both the geyser object AND
    in WORLD['structures']. Requires station_resources water >= 5.
    """

    def setUp(self):
        self.agent = _reset_agent(pos=[5, 5])
        self._orig_structures = list(WORLD.get("structures", []))
        WORLD["structures"] = []
        self._orig_obstacles = list(WORLD.get("obstacles", []))
        WORLD["obstacles"] = []
        _ensure_resources()
        WORLD["station_resources"]["water"] = 10  # Enough for one gas plant (costs 5)

    def tearDown(self):
        WORLD["structures"] = self._orig_structures
        WORLD["obstacles"] = self._orig_obstacles

    def test_build_gas_plant_success(self):
        geyser = _place_geyser([5, 6], state="idle")
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["geyser_position"], [5, 6])
        # Gas plant should be set on geyser object
        self.assertTrue(geyser.get("has_gas_plant"))
        self.assertIsNotNone(geyser.get("gas_plant"))
        # Gas plant should also be in structures
        self.assertEqual(len([s for s in WORLD["structures"] if s.get("type") == "gas_plant"]), 1)
        # Station water should be deducted
        self.assertEqual(WORLD["station_resources"]["water"], 5)  # 10 - 5

    def test_build_gas_plant_no_geyser(self):
        """Rover with no adjacent geyser fails."""
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertFalse(result["ok"])
        self.assertIn("geyser", result["error"].lower())

    def test_build_gas_plant_duplicate(self):
        """Cannot build two gas plants on same geyser."""
        _place_geyser([5, 6], state="idle")
        WORLD["station_resources"]["water"] = 20  # Enough for two attempts
        first = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertTrue(first["ok"])
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertFalse(result["ok"])
        self.assertIn("already", result["error"].lower())

    def test_build_gas_plant_low_battery(self):
        """Low battery prevents building."""
        _place_geyser([5, 6], state="idle")
        self.agent["battery"] = 0.001
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())

    def test_build_gas_plant_insufficient_water(self):
        """Cannot build gas plant without enough station water."""
        _place_geyser([5, 6], state="idle")
        WORLD["station_resources"]["water"] = 3  # Need 5
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertFalse(result["ok"])
        self.assertIn("water", result["error"].lower())


class TestUpgradeBase(unittest.TestCase):
    """Tests for the upgrade_base action.

    Uses station_resources (water + gas) and the UPGRADES dict.
    Upgrades are named (e.g. 'charge_mk2') and have max levels.
    """

    def setUp(self):
        self.agent = _reset_agent(pos=[0, 0])  # At station
        _ensure_resources()
        self._orig_station_pos = list(WORLD["agents"]["station"]["position"])
        WORLD["agents"]["station"]["position"] = [0, 0]
        self._orig_station_upgrades = dict(WORLD.get("station_upgrades", {}))
        WORLD["station_upgrades"] = {}
        # Provide plenty of resources
        WORLD["station_resources"]["water"] = 200
        WORLD["station_resources"]["gas"] = 200

    def tearDown(self):
        WORLD["agents"]["station"]["position"] = self._orig_station_pos
        WORLD["station_upgrades"] = self._orig_station_upgrades

    def test_upgrade_charge_mk2(self):
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["upgrade"], "charge_mk2")
        self.assertEqual(result["new_level"], 1)
        self.assertEqual(WORLD["station_upgrades"]["charge_mk2"], 1)
        # Resources should be deducted
        cfg = UPGRADES["charge_mk2"]
        self.assertEqual(WORLD["station_resources"]["water"], 200 - cfg["water"])
        self.assertEqual(WORLD["station_resources"]["gas"], 200 - cfg["gas"])

    def test_upgrade_not_at_station(self):
        """Cannot upgrade when not at station."""
        self.agent["position"] = [5, 5]
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("station", result["error"].lower())

    def test_upgrade_insufficient_resources(self):
        """Cannot upgrade without sufficient resources."""
        WORLD["station_resources"]["water"] = 0
        WORLD["station_resources"]["gas"] = 0
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("water", result["error"].lower())

    def test_upgrade_invalid_type(self):
        """Cannot upgrade with invalid upgrade type."""
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "invalid"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown upgrade", result["error"])

    def test_upgrade_max_level(self):
        """Cannot exceed max level for an upgrade."""
        cfg = UPGRADES["charge_mk2"]
        # Upgrade to max level
        for i in range(cfg["max_level"]):
            result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
            self.assertTrue(result["ok"], f"Upgrade {i + 1} should succeed")
        # One more should fail
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())


class TestGasProduction(unittest.TestCase):
    """Tests for gas plant production during tick updates.

    Gas production actually happens inside update_geysers() when a geyser
    transitions to 'erupting' and has an active gas_plant. update_gas_plants()
    is intentionally a no-op.
    """

    def setUp(self):
        _ensure_resources()

    def test_update_gas_plants_stub(self):
        """update_gas_plants() returns 0 (gas production handled by update_geysers)."""
        from app.world import update_gas_plants

        produced = update_gas_plants()
        self.assertEqual(produced, 0)


if __name__ == "__main__":
    unittest.main()
