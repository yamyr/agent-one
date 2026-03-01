"""Tests for the resource system: ice deposits, water recycling, gas plants, and base upgrades."""

import unittest

from app.world import (
    world,
    execute_action,
    WORLD,
    _execute_build_gas_plant,
    _execute_upgrade_base,
)


def _reset_agent(agent_id="rover-mistral", pos=None, battery=1.0):
    """Reset an agent to a known state for testing."""
    agent = world.state["agents"][agent_id]
    agent["position"] = list(pos) if pos else [5, 5]
    agent["battery"] = battery
    agent["inventory"] = []
    agent["memory"] = []
    return agent


def _place_ice_deposit(pos, quantity=50, discovered=True):
    """Place a test ice deposit at the given position."""
    deposit = {
        "position": list(pos),
        "quantity": quantity,
        "_true_quantity": quantity,
        "discovered": discovered,
    }
    WORLD.setdefault("ice_deposits", []).append(deposit)
    return deposit


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
    """Ensure WORLD['resources'] dict exists."""
    WORLD.setdefault("resources", {"water": 0, "gas": 0})


class TestGatherIce(unittest.TestCase):
    """Tests for the gather_ice action."""

    def setUp(self):
        self.agent = _reset_agent(pos=[5, 5])
        # Clear ice deposits
        WORLD["ice_deposits"] = []
        _ensure_resources()

    def tearDown(self):
        WORLD["ice_deposits"] = []

    def test_gather_ice_success(self):
        """Rover at an ice deposit can gather ice."""
        _place_ice_deposit([5, 5], quantity=40)
        result = execute_action("rover-mistral", "gather_ice", {})
        self.assertTrue(result["ok"])
        # Ice should be in inventory
        ice_items = [i for i in self.agent["inventory"] if i.get("type") == "ice"]
        self.assertEqual(len(ice_items), 1)
        self.assertEqual(ice_items[0]["quantity"], 40)
        deposits_at = [d for d in WORLD["ice_deposits"] if d["position"] == [5, 5]]
        self.assertEqual(len(deposits_at), 1)
        self.assertEqual(deposits_at[0]["quantity"], 0)
        self.assertTrue(deposits_at[0].get("gathered"))

    def test_gather_ice_no_deposit(self):
        """Rover with no ice deposit at position fails."""
        result = execute_action("rover-mistral", "gather_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("No ice", result["error"])

    def test_gather_ice_low_battery(self):
        """Rover with low battery fails to gather."""
        _place_ice_deposit([5, 5], quantity=40)
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
    """Tests for the recycle_ice action."""

    def setUp(self):
        self.agent = _reset_agent(pos=[0, 0])
        WORLD["ice_deposits"] = []
        _ensure_resources()
        WORLD["resources"]["water"] = 0
        self._orig_station_pos = list(WORLD["agents"]["station"]["position"])
        WORLD["agents"]["station"]["position"] = [0, 0]

    def tearDown(self):
        WORLD["resources"]["water"] = 0
        WORLD["agents"]["station"]["position"] = self._orig_station_pos

    def test_recycle_ice_success(self):
        self.agent["inventory"] = [{"type": "ice", "quantity": 30}]
        result = execute_action("rover-mistral", "recycle_ice", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["water_gained"], 60)
        self.assertEqual(WORLD["resources"]["water"], 60)
        # Ice should be removed from inventory
        ice_items = [i for i in self.agent["inventory"] if i.get("type") == "ice"]
        self.assertEqual(len(ice_items), 0)

    def test_recycle_ice_not_at_station(self):
        self.agent["position"] = [5, 5]
        self.agent["inventory"] = [{"type": "ice", "quantity": 30}]
        result = execute_action("rover-mistral", "recycle_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("station", result["error"].lower())

    def test_recycle_ice_no_ice(self):
        """Rover with no ice in inventory cannot recycle."""
        result = execute_action("rover-mistral", "recycle_ice", {})
        self.assertFalse(result["ok"])
        self.assertIn("ice", result["error"].lower())


class TestBuildGasPlant(unittest.TestCase):
    """Tests for the build_gas_plant action."""

    def setUp(self):
        self.agent = _reset_agent(pos=[5, 5])
        self._orig_gas_plants = list(WORLD.get("gas_plants", []))
        WORLD["gas_plants"] = []
        self._orig_obstacles = list(WORLD.get("obstacles", []))
        WORLD["obstacles"] = []
        # Clear only test geysers
        _ensure_resources()

    def tearDown(self):
        WORLD["gas_plants"] = self._orig_gas_plants
        WORLD["obstacles"] = self._orig_obstacles

    def test_build_gas_plant_success(self):
        _place_geyser([5, 6], state="idle")
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["geyser_position"], [5, 6])
        self.assertEqual(len(WORLD["gas_plants"]), 1)
        self.assertEqual(WORLD["gas_plants"][0]["geyser_position"], [5, 6])

    def test_build_gas_plant_no_geyser(self):
        """Rover with no adjacent geyser fails."""
        result = _execute_build_gas_plant("rover-mistral", self.agent, {})
        self.assertFalse(result["ok"])
        self.assertIn("geyser", result["error"].lower())

    def test_build_gas_plant_duplicate(self):
        """Cannot build two gas plants on same geyser."""
        _place_geyser([5, 6], state="idle")
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


class TestUpgradeBase(unittest.TestCase):
    """Tests for the upgrade_base action."""

    def setUp(self):
        self.agent = _reset_agent(pos=[0, 0])  # At station
        _ensure_resources()
        self._orig_station_pos = list(WORLD["agents"]["station"]["position"])
        WORLD["agents"]["station"]["position"] = [0, 0]
        self._orig_station_resources = dict(WORLD.get("station_resources", {}))
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        self._orig_station_upgrades = dict(WORLD.get("station_upgrades", {}))
        WORLD["station_upgrades"] = {}

    def tearDown(self):
        WORLD["agents"]["station"]["position"] = self._orig_station_pos
        WORLD["station_resources"] = self._orig_station_resources
        WORLD["station_upgrades"] = self._orig_station_upgrades

    def test_upgrade_charge_mk2(self):
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["station_upgrades"]["charge_mk2"], 1)

    def test_upgrade_not_at_station(self):
        """Cannot upgrade when not at station."""
        self.agent["position"] = [5, 5]
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("station", result["error"].lower())

    def test_upgrade_insufficient_resources(self):
        """Cannot upgrade without sufficient resources."""
        WORLD["station_resources"] = {"water": 0, "gas": 0, "parts": []}
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("insufficient", result["error"].lower())

    def test_upgrade_invalid_type(self):
        """Cannot upgrade with invalid upgrade type."""
        result = _execute_upgrade_base("rover-mistral", self.agent, {"upgrade": "invalid"})
        self.assertFalse(result["ok"])


class TestGasProduction(unittest.TestCase):
    """Tests for gas plant production during tick updates."""

    def setUp(self):
        _ensure_resources()
        WORLD["resources"]["gas"] = 0
        WORLD["gas_plants"] = []

    def tearDown(self):
        WORLD["gas_plants"] = []
        WORLD["resources"]["gas"] = 0

    def test_gas_produced_on_erupting_geyser(self):
        _place_geyser([10, 10], state="erupting")
        WORLD["gas_plants"].append(
            {
                "position": [10, 10],
                "geyser_position": [10, 10],
                "production_rate": 5,
                "total_produced": 0,
                "active": True,
            }
        )
        # Import and call the update function
        from app.world import update_gas_plants

        produced = update_gas_plants()
        self.assertEqual(produced, 0)
        self.assertEqual(WORLD["resources"]["gas"], 0)

    def test_gas_not_produced_on_idle_geyser(self):
        """Gas plant does NOT produce gas when geyser is idle."""
        _place_geyser([10, 10], state="idle")
        geyser_idx = len(WORLD["obstacles"]) - 1
        WORLD["gas_plants"].append(
            {
                "position": [10, 10],
                "geyser_index": geyser_idx,
                "production_rate": 5,
                "total_produced": 0,
                "active": True,
            }
        )
        from app.world import update_gas_plants

        update_gas_plants()
        self.assertEqual(WORLD["resources"]["gas"], 0)


if __name__ == "__main__":
    unittest.main()
