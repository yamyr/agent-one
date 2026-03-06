"""Comprehensive upgrade system contract tests.

Covers base upgrades (charge_mk2, extended_fuel, enhanced_scanner, repair_bay),
building upgrades (refinery, solar_panel_structure, accumulator), multi-level
progression, and integration flows.
"""

import copy
import unittest

from app import storm as storm_mod
from app.world import (
    CHARGE_RATE,
    FUEL_CAPACITY_ROVER,
    ROVER_REVEAL_RADIUS,
    STRUCTURE_TYPES,
    UPGRADES,
    WORLD,
    _apply_upgrade_bonuses,
    _effective_fuel_capacity,
    _execute_charge,
    _execute_upgrade_base,
    _get_upgrade_level,
    _reveal_radius_for,
    check_mission_status,
    execute_action,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
            "base_effects": copy.deepcopy(WORLD.get("base_effects", {})),
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
        WORLD["base_effects"] = {}

        # Reset rover to station position
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [0, 0]
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

    def tearDown(self):
        WORLD["agents"]["rover-mistral"] = self._saved_rover
        WORLD["agents"]["hauler-mistral"] = self._saved_hauler
        WORLD["agents"]["station"] = self._saved_station

        for key, val in self._saved_world.items():
            WORLD[key] = val


def _make_structure(stype="solar_panel_structure", pos=(5, 6), active=True, upgrade_level=1):
    """Create a structure dict with contents from STRUCTURE_TYPES templates."""
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


# ---------------------------------------------------------------------------
# US1: Base Upgrade Contract Tests
# ---------------------------------------------------------------------------


class TestBaseUpgradeSuccess(_WorldSaveRestore):
    """Tests that each base upgrade type succeeds with correct prerequisites."""

    def _setup_resources(self, water=100, gas=100):
        WORLD["station_resources"] = {"water": water, "gas": gas, "parts": []}

    def test_charge_mk2_succeeds(self):
        self._setup_resources()
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["new_level"], 1)
        self.assertEqual(result["cost"], {"water": 50, "gas": 20})

    def test_extended_fuel_succeeds(self):
        self._setup_resources()
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "extended_fuel"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["new_level"], 1)
        self.assertEqual(result["cost"], {"water": 30, "gas": 10})

    def test_enhanced_scanner_succeeds(self):
        self._setup_resources()
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "enhanced_scanner"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["new_level"], 1)
        self.assertEqual(result["cost"], {"water": 20, "gas": 15})

    def test_repair_bay_succeeds(self):
        self._setup_resources()
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "repair_bay"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["new_level"], 1)
        self.assertEqual(result["cost"], {"water": 40, "gas": 30})

    def test_resource_deduction_exact(self):
        """Each upgrade type deducts exactly the water/gas amounts from UPGRADES config."""
        for upgrade_name, cfg in UPGRADES.items():
            WORLD["station_upgrades"] = {}
            WORLD["station_resources"] = {"water": 200, "gas": 200, "parts": []}
            rover = WORLD["agents"]["rover-mistral"]
            _execute_upgrade_base("rover-mistral", rover, {"upgrade": upgrade_name})
            self.assertEqual(
                WORLD["station_resources"]["water"],
                200 - cfg["water"],
                f"{upgrade_name}: water deduction mismatch",
            )
            self.assertEqual(
                WORLD["station_resources"]["gas"],
                200 - cfg["gas"],
                f"{upgrade_name}: gas deduction mismatch",
            )

    def test_return_value_structure(self):
        """Successful upgrade returns dict with expected keys."""
        self._setup_resources()
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})
        for key in ("ok", "upgrade", "new_level", "cost", "description"):
            self.assertIn(key, result, f"Missing key: {key}")
        self.assertIsInstance(result["cost"], dict)
        self.assertIn("water", result["cost"])
        self.assertIn("gas", result["cost"])


class TestBaseUpgradeEffects(_WorldSaveRestore):
    """Tests that each upgrade type's gameplay effect is correctly applied."""

    def test_charge_mk2_doubles_charge_rate(self):
        """With charge_mk2 active, charge rate is 2x the base CHARGE_RATE."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["battery"] = 0.1

        # Charge without upgrade
        WORLD["station_upgrades"] = {}
        result_before = _execute_charge("rover-mistral", rover)
        self.assertTrue(result_before["ok"])
        rate_without = result_before["charge_rate"]

        # Reset battery for second charge
        rover["battery"] = 0.1
        WORLD["station_upgrades"] = {"charge_mk2": 1}
        result_after = _execute_charge("rover-mistral", rover)
        self.assertTrue(result_after["ok"])
        rate_with = result_after["charge_rate"]

        self.assertAlmostEqual(rate_with, rate_without * 2, places=6)
        self.assertAlmostEqual(rate_with, CHARGE_RATE * 2, places=6)

    def test_extended_fuel_adds_100_capacity(self):
        """With extended_fuel at level 1, rover fuel capacity increases by 100."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["type"] = "rover"
        WORLD["station_upgrades"] = {}
        base_capacity = _effective_fuel_capacity(rover)
        self.assertEqual(base_capacity, FUEL_CAPACITY_ROVER)

        WORLD["station_upgrades"] = {"extended_fuel": 1}
        upgraded_capacity = _effective_fuel_capacity(rover)
        self.assertEqual(upgraded_capacity, FUEL_CAPACITY_ROVER + 100)

    def test_enhanced_scanner_adds_1_radius(self):
        """With enhanced_scanner at level 1, rover reveal radius increases by 1."""
        rover = WORLD["agents"]["rover-mistral"]
        WORLD["station_upgrades"] = {}
        base_radius = _reveal_radius_for(rover)
        self.assertEqual(base_radius, ROVER_REVEAL_RADIUS)

        WORLD["station_upgrades"] = {"enhanced_scanner": 1}
        upgraded_radius = _reveal_radius_for(rover)
        self.assertEqual(upgraded_radius, ROVER_REVEAL_RADIUS + 1)

    def test_repair_bay_auto_repairs_at_station(self):
        """With repair_bay active, rover at station gets battery set to 1.0 during tick."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["battery"] = 0.5
        rover["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["station_upgrades"] = {"repair_bay": 1}

        # check_mission_status iterates agents and applies repair_bay
        check_mission_status()
        self.assertEqual(rover["battery"], 1.0)

    def test_repair_bay_inactive_does_not_repair(self):
        """Without repair_bay, rover battery is not auto-set to 1.0."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["battery"] = 0.5
        rover["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["station_upgrades"] = {}

        check_mission_status()
        # Battery should NOT be changed to 1.0 by repair_bay
        self.assertLessEqual(rover["battery"], 0.5)


class TestBaseUpgradeFailures(_WorldSaveRestore):
    """Tests failure cases for base upgrades."""

    def test_wrong_position(self):
        """Upgrade fails when rover is not at station."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("station", result["error"].lower())

    def test_insufficient_water_only(self):
        """Upgrade fails when water is insufficient but gas is sufficient."""
        WORLD["station_resources"] = {"water": 0, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("water", result["error"].lower())

    def test_insufficient_gas_only(self):
        """Upgrade fails when gas is insufficient but water is sufficient."""
        WORLD["station_resources"] = {"water": 100, "gas": 0, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("gas", result["error"].lower())

    def test_unknown_upgrade_name(self):
        """Upgrade fails for an unrecognized upgrade name."""
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "warp_drive"})
        self.assertFalse(result["ok"])
        self.assertIn("unknown", result["error"].lower())

    def test_max_level_charge_mk2(self):
        """charge_mk2 (max_level=1) cannot be upgraded past level 1."""
        WORLD["station_upgrades"] = {"charge_mk2": 1}
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())

    def test_max_level_extended_fuel(self):
        """extended_fuel (max_level=2) cannot be upgraded past level 2."""
        WORLD["station_upgrades"] = {"extended_fuel": 2}
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "extended_fuel"})
        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())

    def test_max_level_enhanced_scanner(self):
        """enhanced_scanner (max_level=2) cannot be upgraded past level 2."""
        WORLD["station_upgrades"] = {"enhanced_scanner": 2}
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "enhanced_scanner"})
        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())

    def test_max_level_repair_bay(self):
        """repair_bay (max_level=1) cannot be upgraded past level 1."""
        WORLD["station_upgrades"] = {"repair_bay": 1}
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "repair_bay"})
        self.assertFalse(result["ok"])
        self.assertIn("max level", result["error"].lower())

    def test_drone_cannot_upgrade_base(self):
        """Drones are blocked from using upgrade_base action."""
        result = execute_action("drone-mistral", "upgrade_base", {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("drone", result["error"].lower())

    def test_hauler_cannot_upgrade_base(self):
        """Haulers are blocked from using upgrade_base action."""
        result = execute_action("hauler-mistral", "upgrade_base", {"upgrade": "charge_mk2"})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_missing_upgrade_param(self):
        """Upgrade fails when no upgrade name is provided."""
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        result = _execute_upgrade_base("rover-mistral", rover, {})
        self.assertFalse(result["ok"])
        self.assertIn("unknown", result["error"].lower())


# ---------------------------------------------------------------------------
# US2: Building Upgrade Contract Tests
# ---------------------------------------------------------------------------


class TestBuildingUpgradeBonuses(unittest.TestCase):
    """Tests bonus calculations at each level for each structure type."""

    def test_refinery_level2_bonus(self):
        """Refinery at level 2: processing_capacity = int(round(50 * 1.5)) = 75."""
        structure = _make_structure("refinery")
        structure["upgrade_level"] = 2
        _apply_upgrade_bonuses(structure)
        self.assertEqual(structure["contents"]["processing_capacity"], int(round(50 * 1.5)))

    def test_refinery_level3_bonus(self):
        """Refinery at level 3: processing_capacity = int(round(50 * 2.25)) = 112."""
        structure = _make_structure("refinery")
        structure["upgrade_level"] = 3
        _apply_upgrade_bonuses(structure)
        self.assertEqual(structure["contents"]["processing_capacity"], int(round(50 * 2.25)))

    def test_solar_panel_level2_bonus(self):
        """Solar panel at level 2: charge_rate * 1.5, charge_radius + 1."""
        structure = _make_structure("solar_panel_structure")
        structure["upgrade_level"] = 2
        _apply_upgrade_bonuses(structure)
        self.assertAlmostEqual(structure["contents"]["charge_rate"], round(0.01 * 1.5, 5), places=5)
        self.assertEqual(structure["contents"]["charge_radius"], 2)

    def test_solar_panel_level3_bonus(self):
        """Solar panel at level 3: charge_rate * 2.25, charge_radius + 2."""
        structure = _make_structure("solar_panel_structure")
        structure["upgrade_level"] = 3
        _apply_upgrade_bonuses(structure)
        self.assertAlmostEqual(
            structure["contents"]["charge_rate"], round(0.01 * 2.25, 5), places=5
        )
        self.assertEqual(structure["contents"]["charge_radius"], 3)

    def test_accumulator_level2_bonus(self):
        """Accumulator at level 2: recharge_rate * 1.5, recharge_interval 5-1=4."""
        structure = _make_structure("accumulator")
        structure["upgrade_level"] = 2
        _apply_upgrade_bonuses(structure)
        self.assertAlmostEqual(
            structure["contents"]["recharge_rate"], round(0.01 * 1.5, 5), places=5
        )
        self.assertEqual(structure["contents"]["recharge_interval"], 4)

    def test_accumulator_level3_bonus(self):
        """Accumulator at level 3: recharge_rate * 2.25, recharge_interval 5-2=3."""
        structure = _make_structure("accumulator")
        structure["upgrade_level"] = 3
        _apply_upgrade_bonuses(structure)
        self.assertAlmostEqual(
            structure["contents"]["recharge_rate"], round(0.01 * 2.25, 5), places=5
        )
        self.assertEqual(structure["contents"]["recharge_interval"], 3)

    def test_accumulator_interval_clamp_at_1(self):
        """Accumulator with base interval=1 at level 3: max(1, 1-2) = 1."""
        structure = _make_structure("accumulator")
        structure["contents"]["recharge_interval"] = 1
        structure["upgrade_level"] = 3
        _apply_upgrade_bonuses(structure)
        self.assertEqual(structure["contents"]["recharge_interval"], 1)

    def test_upgrade_one_structure_does_not_affect_other(self):
        """Upgrading one structure leaves other structures unchanged."""
        refinery = _make_structure("refinery", pos=(5, 6))
        solar = _make_structure("solar_panel_structure", pos=(7, 8))
        original_solar_contents = dict(solar["contents"])

        refinery["upgrade_level"] = 2
        _apply_upgrade_bonuses(refinery)

        # Solar panel should be unchanged
        self.assertEqual(solar["contents"], original_solar_contents)


class TestBuildingUpgradeFailures(_WorldSaveRestore):
    """Tests failure cases for building upgrades."""

    def test_drone_cannot_upgrade_building(self):
        """Drones are blocked from using upgrade_building action."""
        WORLD["structures"] = [_make_structure(pos=(5, 6))]
        result = execute_action("drone-mistral", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("drone", result["error"].lower())

    def test_hauler_cannot_upgrade_building(self):
        """Haulers are blocked from using upgrade_building action."""
        WORLD["structures"] = [_make_structure(pos=(5, 6))]
        result = execute_action("hauler-mistral", "upgrade_building", {})
        self.assertFalse(result["ok"])
        self.assertIn("hauler", result["error"].lower())

    def test_building_upgrade_return_value_structure(self):
        """Successful building upgrade returns dict with expected keys."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [5, 5]
        rover["battery"] = 1.0
        rover["inventory"] = [
            {"type": "basalt_vein", "grade": "low", "quantity": 25},
        ]
        WORLD["structures"] = [_make_structure(pos=(5, 6))]
        result = execute_action("rover-mistral", "upgrade_building", {})
        self.assertTrue(result["ok"])
        for key in ("ok", "structure_type", "new_level", "position"):
            self.assertIn(key, result, f"Missing key: {key}")


# ---------------------------------------------------------------------------
# US3: Multi-Level and Integration Tests
# ---------------------------------------------------------------------------


class TestMultiLevelUpgrades(_WorldSaveRestore):
    """Tests multi-level upgrade progression and cumulative effects."""

    def test_extended_fuel_level2_adds_200(self):
        """Two levels of extended_fuel adds 200 to fuel capacity."""
        rover = WORLD["agents"]["rover-mistral"]
        rover["type"] = "rover"
        WORLD["station_resources"] = {"water": 200, "gas": 200, "parts": []}

        # Level 1
        result1 = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "extended_fuel"})
        self.assertTrue(result1["ok"])
        self.assertEqual(result1["new_level"], 1)
        self.assertEqual(_effective_fuel_capacity(rover), FUEL_CAPACITY_ROVER + 100)

        # Level 2
        result2 = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "extended_fuel"})
        self.assertTrue(result2["ok"])
        self.assertEqual(result2["new_level"], 2)
        self.assertEqual(_effective_fuel_capacity(rover), FUEL_CAPACITY_ROVER + 200)

    def test_enhanced_scanner_level2_adds_2_radius(self):
        """Two levels of enhanced_scanner adds 2 to reveal radius."""
        rover = WORLD["agents"]["rover-mistral"]
        WORLD["station_resources"] = {"water": 200, "gas": 200, "parts": []}

        result1 = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "enhanced_scanner"})
        self.assertTrue(result1["ok"])
        self.assertEqual(_reveal_radius_for(rover), ROVER_REVEAL_RADIUS + 1)

        result2 = _execute_upgrade_base("rover-mistral", rover, {"upgrade": "enhanced_scanner"})
        self.assertTrue(result2["ok"])
        self.assertEqual(_reveal_radius_for(rover), ROVER_REVEAL_RADIUS + 2)

    def test_building_re_upgrade_uses_base_contents(self):
        """Re-upgrading a building preserves _base_contents and calculates from base."""
        structure = _make_structure("solar_panel_structure")
        base_rate = structure["contents"]["charge_rate"]
        base_radius = structure["contents"]["charge_radius"]

        # Upgrade to level 2
        structure["upgrade_level"] = 2
        _apply_upgrade_bonuses(structure)
        self.assertIn("_base_contents", structure)
        self.assertAlmostEqual(
            structure["contents"]["charge_rate"], round(base_rate * 1.5, 5), places=5
        )

        # Upgrade to level 3 -- bonuses should be from base, not from level-2 values
        structure["upgrade_level"] = 3
        _apply_upgrade_bonuses(structure)
        self.assertAlmostEqual(
            structure["contents"]["charge_rate"], round(base_rate * 2.25, 5), places=5
        )
        self.assertEqual(structure["contents"]["charge_radius"], base_radius + 2)


class TestUpgradeIntegration(_WorldSaveRestore):
    """Integration tests for upgrade flows."""

    def test_full_base_upgrade_flow(self):
        """Full flow: set resources, upgrade via execute_action, verify effect."""
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [0, 0]

        # Upgrade via execute_action (tests the routing layer)
        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "enhanced_scanner"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["upgrade"], "enhanced_scanner")

        # Verify resources deducted
        self.assertEqual(WORLD["station_resources"]["water"], 100 - 20)
        self.assertEqual(WORLD["station_resources"]["gas"], 100 - 15)

        # Verify effect applied
        self.assertEqual(_get_upgrade_level("enhanced_scanner"), 1)
        self.assertEqual(_reveal_radius_for(rover), ROVER_REVEAL_RADIUS + 1)

    def test_upgrade_during_storm(self):
        """Base upgrade succeeds during an active storm (storms don't block upgrades)."""
        WORLD["station_resources"] = {"water": 100, "gas": 100, "parts": []}
        WORLD["storm"] = {
            "phase": "active",
            "next_storm_tick": 0,
            "active_start": 0,
            "active_end": 100,
            "intensity": 0.8,
            "warning_start": 0,
        }
        rover = WORLD["agents"]["rover-mistral"]
        rover["position"] = [0, 0]

        result = execute_action("rover-mistral", "upgrade_base", {"upgrade": "charge_mk2"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["new_level"], 1)
