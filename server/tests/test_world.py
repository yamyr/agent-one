import unittest

from app.world import WORLD, move_agent, execute_action, get_snapshot, check_ground
from app.world import check_mission_status, charge_rover, charge_agent
from app.world import BATTERY_COST_MOVE, BATTERY_COST_DIG, BATTERY_COST_PICKUP
from app.world import BATTERY_COST_ANALYZE, BATTERY_COST_ANALYZE_GROUND
from app.world import BATTERY_COST_SCAN, BATTERY_COST_MOVE_DRONE
from app.world import CHARGE_RATE, REVEAL_RADIUS, ROVER_REVEAL_RADIUS, DRONE_REVEAL_RADIUS
from app.world import AGENT_STARTS
from app.world import assign_mission, _cells_in_radius, record_memory, MEMORY_MAX
from app.world import update_tasks, _direction_hint


class TestMoveAgent(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [2, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[2, 10]]

    def test_move_success(self):
        result = move_agent("rover-mock", 3, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [3, 10])

    def test_move_negative_coords_allowed(self):
        """Infinite grid: negative coordinates are valid."""
        WORLD["agents"]["rover-mock"]["position"] = [0, 10]
        result = move_agent("rover-mock", -1, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["to"], [-1, 10])

    def test_move_beyond_old_bounds_allowed(self):
        """Infinite grid: moving beyond old 20x20 bounds is valid."""
        WORLD["agents"]["rover-mock"]["position"] = [19, 10]
        result = move_agent("rover-mock", 20, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["to"], [20, 10])

    def test_move_too_far(self):
        result = move_agent("rover-mock", 6, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Too far", result["error"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [2, 10])

    def test_move_diagonal_rejected(self):
        result = move_agent("rover-mock", 3, 11)
        self.assertFalse(result["ok"])
        self.assertIn("Not a straight line", result["error"])

    def test_move_multi_tile(self):
        result = move_agent("rover-mock", 5, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 3)
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [5, 10])

    def test_move_2_tiles(self):
        result = move_agent("rover-mock", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 2)

    def test_move_already_there(self):
        result = move_agent("rover-mock", 2, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Already at", result["error"])

    def test_move_unknown_agent(self):
        result = move_agent("rover-99", 3, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_move_sequential(self):
        move_agent("rover-mock", 3, 10)
        result = move_agent("rover-mock", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [3, 10])
        self.assertEqual(result["to"], [4, 10])

    def test_move_all_four_directions(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        for tx, ty in [(11, 10), (10, 10), (10, 11), (10, 10)]:
            result = move_agent("rover-mock", tx, ty)
            self.assertTrue(result["ok"])

    def test_get_snapshot_is_copy(self):
        snap = get_snapshot()
        snap["agents"]["rover-mock"]["position"] = [99, 99]
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [2, 10])

    def test_snapshot_has_grid(self):
        snap = get_snapshot()
        self.assertEqual(snap["grid"]["w"], 20)
        self.assertEqual(snap["grid"]["h"], 20)


class TestExecuteAction(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [2, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[2, 10]]

    def test_execute_move_east(self):
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [3, 10])

    def test_execute_move_drains_battery(self):
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_MOVE)

    def test_execute_move_negative_ok(self):
        """Infinite grid: moving to negative coords succeeds."""
        WORLD["agents"]["rover-mock"]["position"] = [0, 10]
        result = execute_action("rover-mock", "move", {"direction": "west"})
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [-1, 10])

    def test_execute_move_invalid_direction(self):
        result = execute_action("rover-mock", "move", {"direction": "up"})
        self.assertFalse(result["ok"])
        self.assertIn("Invalid direction", result["error"])

    def test_execute_unknown_action(self):
        result = execute_action("rover-mock", "drill", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])

    def test_execute_unknown_agent(self):
        result = execute_action("rover-99", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_execute_move_all_directions(self):
        """North = +Y, South = -Y with flipped coordinate system."""
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        for direction, expected in [
            ("north", [10, 11]),
            ("south", [10, 9]),
            ("east", [11, 10]),
            ("west", [10, 10]),
        ]:
            result = execute_action("rover-mock", "move", {"direction": direction})
            self.assertTrue(result["ok"], f"Failed for direction {direction}")

    def test_execute_move_multi_tile(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        result = execute_action("rover-mock", "move", {"direction": "east", "distance": 3})
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [13, 10])
        self.assertAlmostEqual(
            WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_MOVE * 3
        )

    def test_execute_move_multi_visits_intermediate(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        execute_action("rover-mock", "move", {"direction": "east", "distance": 3})
        visited = WORLD["agents"]["rover-mock"]["visited"]
        self.assertIn([11, 10], visited)
        self.assertIn([12, 10], visited)
        self.assertIn([13, 10], visited)

    def test_execute_move_no_battery(self):
        """Move should fail when battery is too low."""
        WORLD["agents"]["rover-mock"]["battery"] = 0.0
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [2, 10])

    def test_execute_move_insufficient_battery_multi(self):
        """Multi-tile move should fail when battery < cost for full distance."""
        WORLD["agents"]["rover-mock"]["battery"] = (
            BATTERY_COST_MOVE * 2
        )  # enough for ~1-2 tiles, not 3
        result = execute_action("rover-mock", "move", {"direction": "east", "distance": 3})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [2, 10])

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        agent = snap["agents"]["rover-mock"]
        self.assertIn("mission", agent)
        self.assertEqual(agent["mission"]["objective"], "Explore the terrain")
        self.assertEqual(agent["mission"]["plan"], [])


class TestStones(unittest.TestCase):
    def test_stones_generated(self):
        """With chunk system, initial chunks generate multiple stones."""
        stones = WORLD["stones"]
        self.assertGreaterEqual(len(stones), 1)  # at least origin chunk's core

    def test_guaranteed_core_stones(self):
        core_count = sum(1 for s in WORLD["stones"] if s["_true_type"] == "core")
        self.assertGreaterEqual(core_count, 1)

    def test_stones_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("stones", snap)
        # Snapshot may have fewer stones due to fog-of-war filtering
        self.assertLessEqual(len(snap["stones"]), len(WORLD["stones"]))

    def test_stone_shape(self):
        for stone in WORLD["stones"]:
            self.assertIn("position", stone)
            self.assertIn("type", stone)
            self.assertIn("_true_type", stone)
            self.assertIn("extracted", stone)
            self.assertIn("analyzed", stone)
            self.assertEqual(len(stone["position"]), 2)
            self.assertIn(stone["_true_type"], ("core", "basalt"))
            self.assertEqual(stone["type"], "unknown")
            self.assertFalse(stone["extracted"])
            self.assertFalse(stone["analyzed"])

    def test_stones_have_valid_positions(self):
        """Stones should have integer coordinate positions (no bounds requirement)."""
        for stone in WORLD["stones"]:
            x, y = stone["position"]
            self.assertIsInstance(x, int)
            self.assertIsInstance(y, int)

    def test_stones_avoid_agent_starts(self):
        for stone in WORLD["stones"]:
            pos = tuple(stone["position"])
            self.assertNotIn(pos, AGENT_STARTS)

    def test_snapshot_strips_true_type(self):
        snap = get_snapshot()
        for stone in snap["stones"]:
            self.assertNotIn("_true_type", stone)

    def test_concentration_map_exists(self):
        """Concentration map key still exists (empty — proximity-based now)."""
        self.assertIn("concentration_map", WORLD)

    def test_concentration_map_serialized_in_snapshot(self):
        snap = get_snapshot()
        conc = snap.get("concentration_map", {})
        # Keys should be "x,y" strings
        for key in conc:
            self.assertIsInstance(key, str)
            self.assertIn(",", key)


class TestVisited(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]

    def test_visited_initial(self):
        self.assertEqual(WORLD["agents"]["rover-mock"]["visited"], [[10, 10]])

    def test_move_updates_visited(self):
        execute_action("rover-mock", "move", {"direction": "east"})
        visited = WORLD["agents"]["rover-mock"]["visited"]
        self.assertIn([11, 10], visited)

    def test_visited_no_duplicates(self):
        execute_action("rover-mock", "move", {"direction": "east"})
        execute_action("rover-mock", "move", {"direction": "west"})
        visited = WORLD["agents"]["rover-mock"]["visited"]
        self.assertEqual(visited.count([10, 10]), 1)


class TestCheckGround(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_check_ground_finds_stone(self):
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        result = check_ground("rover-mock")
        self.assertEqual(result["stone"]["type"], "unknown")
        self.assertFalse(result["stone"]["extracted"])

    def test_check_ground_extracted_stone(self):
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        result = check_ground("rover-mock")
        self.assertEqual(result["stone"]["type"], "core")
        self.assertTrue(result["stone"]["extracted"])

    def test_check_ground_no_stone(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "unknown",
                "_true_type": "basalt",
                "extracted": False,
                "analyzed": False,
            }
        ]
        result = check_ground("rover-mock")
        self.assertIsNone(result["stone"])

    def test_move_result_includes_ground(self):
        WORLD["stones"] = []
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertIn("ground", result)
        self.assertIsNone(result["ground"]["stone"])


class TestAssignMission(unittest.TestCase):
    def setUp(self):
        self._orig = WORLD["agents"]["rover-mock"]["mission"].copy()

    def tearDown(self):
        WORLD["agents"]["rover-mock"]["mission"] = self._orig

    def test_assign_mission_success(self):
        result = assign_mission("rover-mock", "Go to north edge")
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "rover-mock")
        self.assertEqual(result["objective"], "Go to north edge")
        self.assertEqual(WORLD["agents"]["rover-mock"]["mission"]["objective"], "Go to north edge")

    def test_assign_mission_unknown_agent(self):
        result = assign_mission("rover-99", "Go anywhere")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_assign_mission_preserves_plan(self):
        WORLD["agents"]["rover-mock"]["mission"]["plan"] = ["step1"]
        assign_mission("rover-mock", "New objective")
        self.assertEqual(WORLD["agents"]["rover-mock"]["mission"]["plan"], ["step1"])


class TestStationInWorld(unittest.TestCase):
    def test_station_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("station", snap["agents"])
        station = snap["agents"]["station"]
        self.assertEqual(station["type"], "station")
        self.assertEqual(station["position"], [0, 0])
        self.assertIn("mission", station)
        self.assertIn("battery", station)

    def test_station_start_in_agent_starts(self):
        self.assertIn((0, 0), AGENT_STARTS)


class TestAnalyze(unittest.TestCase):
    """Test the analyze action that reveals hidden stone types."""

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[5, 5]]
        WORLD["agents"]["rover-mock"]["memory"] = []
        self._original_stones = WORLD.get("stones", [])
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_analyze_reveals_type(self):
        result = execute_action("rover-mock", "analyze", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "core")
        self.assertTrue(WORLD["stones"][0]["analyzed"])
        self.assertEqual(WORLD["stones"][0]["type"], "core")

    def test_analyze_drains_battery(self):
        execute_action("rover-mock", "analyze", {})
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_ANALYZE)

    def test_analyze_no_stone(self):
        WORLD["stones"] = []
        result = execute_action("rover-mock", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("No stone", result["error"])

    def test_analyze_already_analyzed(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": False,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mock", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("already analyzed", result["error"])

    def test_analyze_unknown_agent(self):
        result = execute_action("rover-99", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_analyze_not_enough_battery(self):
        WORLD["agents"]["rover-mock"]["battery"] = BATTERY_COST_ANALYZE * 0.5  # below analyze cost
        result = execute_action("rover-mock", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_analyze_records_memory(self):
        execute_action("rover-mock", "analyze", {})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Analyzed", mem[0])
        self.assertIn("core", mem[0])


class TestAnalyzeGround(unittest.TestCase):
    """Test the analyze_ground action that reads concentration."""

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[5, 5]]
        WORLD["agents"]["rover-mock"]["memory"] = []
        WORLD["agents"]["rover-mock"]["ground_readings"] = {}

    def test_analyze_ground_returns_concentration(self):
        result = execute_action("rover-mock", "analyze_ground", {})
        self.assertTrue(result["ok"])
        self.assertIn("concentration", result)
        self.assertGreaterEqual(result["concentration"], 0.0)
        self.assertLessEqual(result["concentration"], 1.0)

    def test_analyze_ground_drains_battery(self):
        execute_action("rover-mock", "analyze_ground", {})
        self.assertAlmostEqual(
            WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_ANALYZE_GROUND
        )

    def test_analyze_ground_stores_reading(self):
        execute_action("rover-mock", "analyze_ground", {})
        readings = WORLD["agents"]["rover-mock"]["ground_readings"]
        self.assertIn("5,5", readings)

    def test_analyze_ground_not_enough_battery(self):
        WORLD["agents"]["rover-mock"]["battery"] = BATTERY_COST_ANALYZE_GROUND * 0.5  # below cost
        result = execute_action("rover-mock", "analyze_ground", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_analyze_ground_records_memory(self):
        execute_action("rover-mock", "analyze_ground", {})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Ground concentration", mem[0])


class TestDig(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[5, 5]]
        self._original_stones = WORLD.get("stones", [])
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": False,
                "analyzed": True,
            }
        ]

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_dig_extracts_stone(self):
        result = execute_action("rover-mock", "dig", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"], {"type": "core"})
        self.assertTrue(WORLD["stones"][0]["extracted"])

    def test_dig_drains_battery(self):
        execute_action("rover-mock", "dig", {})
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_DIG)

    def test_dig_no_stone(self):
        WORLD["stones"] = []
        result = execute_action("rover-mock", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("No stone", result["error"])

    def test_dig_already_extracted(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mock", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("already extracted", result["error"])

    def test_dig_not_enough_battery(self):
        WORLD["agents"]["rover-mock"]["battery"] = BATTERY_COST_DIG * 0.5  # below dig cost
        result = execute_action("rover-mock", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], BATTERY_COST_DIG * 0.5)

    def test_dig_failed_no_drain(self):
        WORLD["stones"] = []
        old_battery = WORLD["agents"]["rover-mock"]["battery"]
        execute_action("rover-mock", "dig", {})
        self.assertEqual(WORLD["agents"]["rover-mock"]["battery"], old_battery)

    def test_dig_requires_analyze(self):
        """Dig should fail if stone is not yet analyzed."""
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        result = execute_action("rover-mock", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("not yet analyzed", result["error"])


class TestPickup(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[5, 5]]
        self._original_stones = WORLD.get("stones", [])
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_pickup_success(self):
        result = execute_action("rover-mock", "pickup", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"], {"type": "core"})
        self.assertEqual(result["inventory_count"], 1)

    def test_pickup_adds_to_inventory(self):
        execute_action("rover-mock", "pickup", {})
        inv = WORLD["agents"]["rover-mock"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["type"], "core")

    def test_pickup_removes_stone_from_world(self):
        execute_action("rover-mock", "pickup", {})
        self.assertEqual(len(WORLD["stones"]), 0)

    def test_pickup_drains_battery(self):
        execute_action("rover-mock", "pickup", {})
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_PICKUP)

    def test_pickup_not_extracted(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": False,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mock", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("not yet extracted", result["error"])

    def test_pickup_no_stone(self):
        WORLD["stones"] = []
        result = execute_action("rover-mock", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("No stone", result["error"])

    def test_pickup_not_enough_battery(self):
        WORLD["agents"]["rover-mock"]["battery"] = 0.0
        result = execute_action("rover-mock", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_pickup_requires_analyze(self):
        """Pickup should fail if stone is not yet analyzed."""
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "unknown",
                "_true_type": "core",
                "extracted": True,
                "analyzed": False,
            }
        ]
        result = execute_action("rover-mock", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("not yet analyzed", result["error"])

    def test_dig_then_pickup(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "basalt",
                "_true_type": "basalt",
                "extracted": False,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mock", "dig", {})
        self.assertTrue(result["ok"])
        result = execute_action("rover-mock", "pickup", {})
        self.assertTrue(result["ok"])
        self.assertEqual(len(WORLD["agents"]["rover-mock"]["inventory"]), 1)
        self.assertEqual(len(WORLD["stones"]), 0)

    def test_analyze_dig_pickup_workflow(self):
        """Full workflow: analyze → dig → pickup."""
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        result = execute_action("rover-mock", "analyze", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "core")
        result = execute_action("rover-mock", "dig", {})
        self.assertTrue(result["ok"])
        result = execute_action("rover-mock", "pickup", {})
        self.assertTrue(result["ok"])
        self.assertEqual(len(WORLD["agents"]["rover-mock"]["inventory"]), 1)


class TestCharge(unittest.TestCase):
    """Charging is a station-only action via charge_rover()."""

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["agents"]["rover-mock"]["battery"] = 0.5
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[0, 0]]
        WORLD["agents"]["rover-mock"]["memory"] = []
        WORLD["agents"]["station"]["position"] = [0, 0]

    def test_charge_rover_success(self):
        result = charge_rover("rover-mock")
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_before"], 0.5)
        self.assertAlmostEqual(result["battery_after"], 0.5 + CHARGE_RATE)

    def test_charge_rover_increases_battery(self):
        charge_rover("rover-mock")
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 0.5 + CHARGE_RATE)

    def test_charge_rover_caps_at_full(self):
        WORLD["agents"]["rover-mock"]["battery"] = 0.95
        charge_rover("rover-mock")
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0)

    def test_charge_rover_already_full(self):
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        result = charge_rover("rover-mock")
        self.assertFalse(result["ok"])
        self.assertIn("already full", result["error"])

    def test_charge_rover_not_at_station(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        result = charge_rover("rover-mock")
        self.assertFalse(result["ok"])
        self.assertIn("Not at station", result["error"])

    def test_charge_rover_multiple_times(self):
        WORLD["agents"]["rover-mock"]["battery"] = 0.1
        charge_rover("rover-mock")
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 0.1 + CHARGE_RATE)
        charge_rover("rover-mock")
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 0.1 + 2 * CHARGE_RATE)

    def test_charge_rover_unknown_agent(self):
        result = charge_rover("rover-99")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_charge_agent_rejects_station(self):
        result = charge_rover("station")
        self.assertFalse(result["ok"])
        self.assertIn("station", result["error"])

    def test_charge_rover_records_memory(self):
        charge_rover("rover-mock")
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_charge_not_available_as_rover_action(self):
        result = execute_action("rover-mock", "charge", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])

    def test_charge_drone_at_station(self):
        """Drones should also charge at station."""
        WORLD["agents"]["drone-mistral"]["position"] = [0, 0]
        WORLD["agents"]["drone-mistral"]["battery"] = 0.5
        result = charge_agent("drone-mistral")
        self.assertTrue(result["ok"])
        self.assertGreater(WORLD["agents"]["drone-mistral"]["battery"], 0.5)

    def test_stone_proximity_concentration(self):
        """get_concentration should return high values near stones."""
        from app.world import get_concentration
        # Place a stone at a known location
        WORLD["stones"].append({"position": [5, 5], "type": "basalt", "_true_type": "basalt"})
        c_at = get_concentration(5, 5)
        c_near = get_concentration(5, 6)
        c_far = get_concentration(5, 15)
        self.assertEqual(c_at, 1.0)
        self.assertGreater(c_near, c_far)


class TestFogOfWar(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]
        WORLD["agents"]["rover-mock"]["revealed"] = [
            [x, y] for x, y in sorted(_cells_in_radius(10, 10, REVEAL_RADIUS))
        ]
        # Give rover-mistral an empty revealed so it doesn't interfere
        WORLD["agents"]["rover-mistral"]["revealed"] = []
        # Give drone an empty revealed so it doesn't interfere
        if "drone-mistral" in WORLD["agents"]:
            self._original_drone_revealed = WORLD["agents"]["drone-mistral"].get("revealed", [])
            WORLD["agents"]["drone-mistral"]["revealed"] = []
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones
        # Restore rover-mistral revealed
        WORLD["agents"]["rover-mistral"]["revealed"] = WORLD["agents"]["rover-mistral"].get(
            "revealed", []
        )
        if "drone-mistral" in WORLD["agents"]:
            WORLD["agents"]["drone-mistral"]["revealed"] = self._original_drone_revealed

    def test_initial_revealed_cells_count(self):
        revealed = WORLD["agents"]["rover-mock"]["revealed"]
        expected = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertEqual(len(revealed), len(expected))

    def test_initial_revealed_contains_start(self):
        revealed = WORLD["agents"]["rover-mock"]["revealed"]
        self.assertIn([10, 10], revealed)

    def test_initial_revealed_contains_neighbors(self):
        revealed = WORLD["agents"]["rover-mock"]["revealed"]
        for pos in [[10, 9], [10, 11], [9, 10], [11, 10]]:
            self.assertIn(pos, revealed)

    def test_move_expands_revealed(self):
        before = len(WORLD["agents"]["rover-mock"]["revealed"])
        execute_action("rover-mock", "move", {"direction": "east"})
        after = len(WORLD["agents"]["rover-mock"]["revealed"])
        self.assertGreater(after, before)

    def test_move_reveals_new_cells(self):
        execute_action("rover-mock", "move", {"direction": "east"})
        revealed = WORLD["agents"]["rover-mock"]["revealed"]
        # (13, 10) is radius-2 east of new position (11, 10)
        self.assertIn([13, 10], revealed)

    def test_move_no_duplicate_revealed(self):
        execute_action("rover-mock", "move", {"direction": "east"})
        execute_action("rover-mock", "move", {"direction": "west"})
        revealed = WORLD["agents"]["rover-mock"]["revealed"]
        # Check no duplicates
        as_tuples = [tuple(c) for c in revealed]
        self.assertEqual(len(as_tuples), len(set(as_tuples)))

    def test_snapshot_hides_unrevealed_stones(self):
        # Place a stone far from any agent's revealed area
        WORLD["stones"] = [
            {
                "position": [19, 19],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 0)

    def test_snapshot_shows_revealed_stones(self):
        # Place a stone within rover-mock's revealed area
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["type"], "unknown")

    def test_snapshot_mixed_visibility(self):
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            },
            {
                "position": [19, 19],
                "type": "unknown",
                "_true_type": "basalt",
                "extracted": False,
                "analyzed": False,
            },
        ]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["position"], [10, 10])

    def test_move_reveals_stone(self):
        # Stone beyond reveal radius — not visible at start, visible after moving east
        WORLD["stones"] = [
            {
                "position": [14, 10],
                "type": "unknown",
                "_true_type": "basalt",
                "extracted": False,
                "analyzed": False,
            }
        ]
        snap_before = get_snapshot()
        self.assertEqual(len(snap_before["stones"]), 0)
        execute_action("rover-mock", "move", {"direction": "east"})
        snap_after = get_snapshot()
        self.assertEqual(len(snap_after["stones"]), 1)

    def test_cells_in_radius_at_corner(self):
        """Infinite grid: cells_in_radius at origin includes negative coords."""
        cells = _cells_in_radius(0, 0, REVEAL_RADIUS)
        # Should include negative coords now (no clamping)
        has_negative = any(x < 0 or y < 0 for x, y in cells)
        self.assertTrue(has_negative)
        # Full diamond at center and corner should be the same size
        center_cells = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertEqual(len(cells), len(center_cells))

    def test_revealed_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("revealed", snap["agents"]["rover-mock"])


class TestMissionCompletion(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[5, 5]]
        WORLD["agents"]["rover-mistral"]["position"] = [2, 12]
        WORLD["agents"]["rover-mistral"]["battery"] = 1.0
        WORLD["agents"]["rover-mistral"]["inventory"] = []
        self._original_stones = WORLD.get("stones", [])
        self._original_mission = WORLD["mission"].copy()
        WORLD["mission"]["status"] = "running"
        WORLD["mission"]["collected_count"] = 0

    def tearDown(self):
        WORLD["stones"] = self._original_stones
        WORLD["mission"] = self._original_mission

    def test_mission_in_world(self):
        self.assertIn("mission", WORLD)
        self.assertEqual(WORLD["mission"]["status"], "running")
        self.assertEqual(WORLD["mission"]["target_type"], "core")
        self.assertEqual(WORLD["mission"]["target_count"], 1)

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("mission", snap)
        self.assertEqual(snap["mission"]["status"], "running")

    def test_collected_count_updates_on_pickup(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        execute_action("rover-mock", "pickup", {})
        self.assertEqual(WORLD["mission"]["collected_count"], 1)

    def test_non_target_stone_not_counted(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "basalt",
                "_true_type": "basalt",
                "extracted": True,
                "analyzed": True,
            }
        ]
        execute_action("rover-mock", "pickup", {})
        self.assertEqual(WORLD["mission"]["collected_count"], 0)

    def test_pickup_away_from_station_no_success(self):
        """Picking up a target stone away from station should NOT trigger success."""
        WORLD["mission"]["target_count"] = 1
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mock", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "running")
        self.assertNotIn("mission", result)
        self.assertEqual(WORLD["mission"]["collected_count"], 1)

    def test_mission_success_on_delivery_to_station(self):
        """Success requires the rover to deliver the stone to the station."""
        WORLD["mission"]["target_count"] = 1
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["stones"] = [
            {
                "position": [0, 0],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mock", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "success")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "success")

    def test_mission_success_on_move_to_station_with_stone(self):
        """Moving to station while carrying target stone triggers success."""
        WORLD["mission"]["target_count"] = 1
        WORLD["agents"]["rover-mock"]["position"] = [1, 0]
        WORLD["agents"]["rover-mock"]["inventory"] = [{"type": "core"}]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["stones"] = []
        result = execute_action("rover-mock", "move", {"direction": "west"})
        self.assertEqual(WORLD["mission"]["status"], "success")
        self.assertIn("mission", result)

    def test_mission_success_with_two_rovers(self):
        WORLD["mission"]["target_count"] = 2
        WORLD["agents"]["station"]["position"] = [0, 0]
        # Rover-mock picks up one core at station
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["stones"] = [
            {
                "position": [0, 0],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        execute_action("rover-mock", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "running")
        # Rover-mistral picks up another core at station
        WORLD["agents"]["rover-mistral"]["position"] = [0, 0]
        WORLD["stones"] = [
            {
                "position": [0, 0],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        result = execute_action("rover-mistral", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "success")
        self.assertEqual(WORLD["mission"]["collected_count"], 2)
        self.assertIn("mission", result)

    def test_mission_failed_all_rovers_depleted(self):
        WORLD["agents"]["rover-mock"]["battery"] = BATTERY_COST_MOVE
        WORLD["agents"]["rover-mistral"]["battery"] = 0.0
        WORLD["agents"]["rover-mistral"]["position"] = [15, 15]
        WORLD["stones"] = []
        # This move will drain rover-mock to 0
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["mission"]["status"], "failed")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "failed")

    def test_rover_at_station_not_failed(self):
        # Even with 0 battery, rover at station can charge — not failed
        WORLD["agents"]["rover-mock"]["battery"] = BATTERY_COST_MOVE
        WORLD["agents"]["rover-mock"]["position"] = [1, 0]
        WORLD["agents"]["rover-mistral"]["battery"] = 0.0
        WORLD["agents"]["rover-mistral"]["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["stones"] = []
        # Move rover-mock, draining to 0 — but rover-mistral is at station
        execute_action("rover-mock", "move", {"direction": "west"})
        self.assertNotEqual(WORLD["mission"]["status"], "failed")

    def test_no_status_change_after_terminal(self):
        WORLD["mission"]["status"] = "success"
        result = check_mission_status()
        self.assertIsNone(result)

    def test_move_does_not_trigger_success(self):
        # Move shouldn't trigger success (no pickup happened)
        WORLD["stones"] = []
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertNotIn("mission", result)


class TestMemory(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]
        WORLD["agents"]["rover-mock"]["memory"] = []
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones
        WORLD["agents"]["rover-mock"]["memory"] = []

    def test_move_records_memory(self):
        WORLD["stones"] = []
        execute_action("rover-mock", "move", {"direction": "east"})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Moved east", mem[0])
        self.assertIn("(11,10)", mem[0])

    def test_move_records_stone_found(self):
        WORLD["stones"] = [
            {
                "position": [11, 10],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        execute_action("rover-mock", "move", {"direction": "east"})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertIn("unknown", mem[0])

    def test_dig_records_memory(self):
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "basalt",
                "_true_type": "basalt",
                "extracted": False,
                "analyzed": True,
            }
        ]
        execute_action("rover-mock", "dig", {})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Dug out basalt", mem[0])

    def test_pickup_records_memory(self):
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        execute_action("rover-mock", "pickup", {})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Picked up core", mem[0])
        self.assertIn("inventory=1", mem[0])

    def test_charge_records_memory(self):
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["agents"]["rover-mock"]["battery"] = 0.5
        charge_rover("rover-mock")
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_failed_action_records_memory(self):
        WORLD["stones"] = []
        execute_action("rover-mock", "dig", {})
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Failed dig", mem[0])

    def test_memory_capped_at_max(self):
        for i in range(MEMORY_MAX + 5):
            record_memory("rover-mock", f"entry {i}")
        mem = WORLD["agents"]["rover-mock"]["memory"]
        self.assertEqual(len(mem), MEMORY_MAX)
        self.assertEqual(mem[0], f"entry {5}")
        self.assertEqual(mem[-1], f"entry {MEMORY_MAX + 4}")

    def test_memory_in_snapshot(self):
        record_memory("rover-mock", "test entry")
        snap = get_snapshot()
        self.assertIn("memory", snap["agents"]["rover-mock"])
        self.assertEqual(snap["agents"]["rover-mock"]["memory"], ["test entry"])

    def test_record_memory_unknown_agent(self):
        # Should not raise
        record_memory("nonexistent", "noop")


class TestDirectionHint(unittest.TestCase):
    """Direction hints use math convention: north = +Y, south = -Y."""

    def test_north(self):
        self.assertEqual(_direction_hint(0, 3), "north")

    def test_south(self):
        self.assertEqual(_direction_hint(0, -3), "south")

    def test_south_east(self):
        self.assertEqual(_direction_hint(2, -5), "south, east")

    def test_north_east(self):
        self.assertEqual(_direction_hint(2, 5), "north, east")

    def test_west(self):
        self.assertEqual(_direction_hint(-1, 0), "west")

    def test_here(self):
        self.assertEqual(_direction_hint(0, 0), "here")


class TestUpdateTasks(unittest.TestCase):
    def setUp(self):
        self._orig_pos = WORLD["agents"]["rover-mock"]["position"][:]
        self._orig_inv = WORLD["agents"]["rover-mock"].get("inventory", [])[:]
        self._orig_stones = WORLD.get("stones", [])[:]
        self._orig_tasks = WORLD["agents"]["rover-mock"].get("tasks", [])[:]
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["inventory"] = []
        WORLD["agents"]["rover-mock"]["tasks"] = []

    def tearDown(self):
        WORLD["agents"]["rover-mock"]["position"] = self._orig_pos
        WORLD["agents"]["rover-mock"]["inventory"] = self._orig_inv
        WORLD["stones"] = self._orig_stones
        WORLD["agents"]["rover-mock"]["tasks"] = self._orig_tasks

    def test_explore_when_no_stones(self):
        WORLD["stones"] = []
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Explore", tasks[0])

    def test_analyze_when_stone_unanalyzed(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Analyze", tasks[0])

    def test_dig_when_stone_analyzed(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": False,
                "analyzed": True,
            }
        ]
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Dig", tasks[0])

    def test_pickup_when_stone_extracted(self):
        WORLD["stones"] = [
            {
                "position": [5, 5],
                "type": "core",
                "_true_type": "core",
                "extracted": True,
                "analyzed": True,
            }
        ]
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Pick up", tasks[0])

    def test_navigate_to_known_stone(self):
        WORLD["stones"] = [
            {
                "position": [8, 5],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            }
        ]
        # Make sure the stone tile is revealed
        agent = WORLD["agents"]["rover-mock"]
        if [8, 5] not in agent.get("revealed", []):
            agent.setdefault("revealed", []).append([8, 5])
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Navigate", tasks[0])
        self.assertIn("east", tasks[0])

    def test_return_to_station_when_has_target(self):
        WORLD["agents"]["rover-mock"]["inventory"] = [{"type": "core"}]
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Return to station", tasks[0])


class TestDrone(unittest.TestCase):
    """Tests for drone agent: creation, scan action, movement, reveal radius."""

    def setUp(self):
        self.drone = WORLD["agents"].get("drone-mistral")
        if self.drone:
            self.drone["position"] = [10, 10]
            self.drone["battery"] = 1.0
            self.drone["visited"] = [[10, 10]]
            self.drone["memory"] = []
        self._original_stones = list(WORLD.get("stones", []))
        WORLD.setdefault("drone_scans", []).clear()

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_drone_exists_in_world(self):
        self.assertIn("drone-mistral", WORLD["agents"])
        self.assertEqual(WORLD["agents"]["drone-mistral"]["type"], "drone")

    def test_drone_reveal_radius_larger(self):
        self.assertGreater(DRONE_REVEAL_RADIUS, ROVER_REVEAL_RADIUS)

    def test_drone_initial_revealed_larger_than_rover(self):
        drone_revealed = len(_cells_in_radius(0, 0, DRONE_REVEAL_RADIUS))
        rover_revealed = len(_cells_in_radius(0, 0, ROVER_REVEAL_RADIUS))
        self.assertGreater(drone_revealed, rover_revealed)

    def test_scan_action(self):
        result = execute_action("drone-mistral", "scan", {})
        self.assertTrue(result["ok"])
        self.assertIn("readings", result)
        self.assertIn("peak", result)
        self.assertEqual(len(WORLD["drone_scans"]), 1)

    def test_scan_battery_cost(self):
        before = self.drone["battery"]
        execute_action("drone-mistral", "scan", {})
        self.assertAlmostEqual(self.drone["battery"], before - BATTERY_COST_SCAN)

    def test_scan_no_battery(self):
        self.drone["battery"] = 0.0
        result = execute_action("drone-mistral", "scan", {})
        self.assertFalse(result["ok"])

    def test_drone_move_max_distance(self):
        result = execute_action("drone-mistral", "move", {"direction": "east", "distance": 6})
        self.assertTrue(result["ok"])
        self.assertEqual(self.drone["position"], [16, 10])

    def test_drone_move_exceeds_max(self):
        result = execute_action("drone-mistral", "move", {"direction": "east", "distance": 7})
        # Should be clamped to MAX_MOVE_DISTANCE_DRONE=6
        self.assertTrue(result["ok"])
        self.assertEqual(self.drone["position"], [16, 10])

    def test_drone_move_battery_cost_lower(self):
        before = self.drone["battery"]
        execute_action("drone-mistral", "move", {"direction": "east", "distance": 1})
        self.assertAlmostEqual(self.drone["battery"], before - BATTERY_COST_MOVE_DRONE)

    def test_drone_cannot_dig(self):
        WORLD["stones"] = [
            {
                "position": [10, 10],
                "type": "core",
                "_true_type": "core",
                "analyzed": True,
                "extracted": False,
            }
        ]
        result = execute_action("drone-mistral", "dig", {})
        self.assertFalse(result["ok"])

    def test_drone_tasks_scan_first(self):
        update_tasks("drone-mistral")
        tasks = self.drone["tasks"]
        self.assertTrue(any("Scan" in t or "scan" in t.lower() for t in tasks))

    def test_rover_tasks_use_drone_scans(self):
        """Rover should suggest navigating to drone-scanned hotspot."""
        WORLD["stones"] = []
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["agents"]["rover-mock"]["visited"] = [[0, 0]]
        WORLD["agents"]["rover-mock"]["revealed"] = [
            [x, y] for x, y in sorted(_cells_in_radius(0, 0, ROVER_REVEAL_RADIUS))
        ]
        WORLD["agents"]["rover-mock"]["inventory"] = []
        # Add a high-concentration drone scan far from rover
        WORLD["drone_scans"] = [
            {
                "position": [15, 15],
                "readings": {"15,15": 0.9, "14,15": 0.7},
                "peak": 0.9,
                "scanner": "drone-mistral",
            }
        ]
        update_tasks("rover-mock")
        tasks = WORLD["agents"]["rover-mock"]["tasks"]
        self.assertTrue(any("hotspot" in t for t in tasks))


class TestChunkSystem(unittest.TestCase):
    """Tests for infinite grid chunk-based procedural generation."""

    def test_chunk_generated_on_move(self):
        """Moving to a far tile generates the chunk."""
        WORLD["agents"]["rover-mock"]["position"] = [30, 30]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        result = move_agent("rover-mock", 31, 30)
        self.assertTrue(result["ok"])
        # Chunk containing (31, 30) should exist
        from app.world import _chunk_key

        ck = _chunk_key(31, 30)
        self.assertIn(ck, WORLD["chunks"])

    def test_chunk_deterministic(self):
        """Same chunk coords always produce same concentration."""
        from app.world import _ensure_chunk, get_concentration, CHUNK_SIZE

        # Generate chunk (5, 5)
        _ensure_chunk(5, 5)
        val1 = get_concentration(5 * CHUNK_SIZE, 5 * CHUNK_SIZE)
        # Re-generating should return cached (same) value
        val2 = get_concentration(5 * CHUNK_SIZE, 5 * CHUNK_SIZE)
        self.assertEqual(val1, val2)

    def test_negative_coords_work(self):
        """Agents can move to and exist at negative coordinates."""
        WORLD["agents"]["rover-mock"]["position"] = [-5, -5]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        result = move_agent("rover-mock", -6, -5)
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [-6, -5])

    def test_bounds_tracking(self):
        """World bounds update when agents move."""
        WORLD["agents"]["rover-mock"]["position"] = [50, 50]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        move_agent("rover-mock", 51, 50)
        bounds = WORLD["bounds"]
        self.assertGreaterEqual(bounds["max_x"], 51)

    def test_origin_chunk_has_core(self):
        """Origin chunk should have at least one core stone."""
        core_stones = [s for s in WORLD["stones"] if s.get("_true_type") == "core"]
        self.assertGreaterEqual(len(core_stones), 1)

    def test_get_concentration_lazy(self):
        """get_concentration generates chunk on demand."""
        from app.world import get_concentration, _chunk_key

        # Access a far-away cell
        val = get_concentration(100, 100)
        self.assertIsInstance(val, float)
        self.assertGreaterEqual(val, 0.0)
        ck = _chunk_key(100, 100)
        self.assertIn(ck, WORLD["chunks"])

    def test_snapshot_includes_bounds(self):
        """Snapshot should include world bounds."""
        snap = get_snapshot()
        self.assertIn("bounds", snap)
        self.assertIn("min_x", snap["bounds"])
        self.assertIn("max_x", snap["bounds"])


class TestSolarPanels(unittest.TestCase):
    """Tests for solar panel deploy and use mechanics."""

    def setUp(self):
        from app.world import reset_world, MAX_SOLAR_PANELS
        reset_world()
        agent = WORLD["agents"]["rover-mock"]
        agent["position"] = [5, 5]
        agent["battery"] = 1.0
        agent["solar_panels_remaining"] = MAX_SOLAR_PANELS

    def test_deploy_solar_panel_success(self):
        result = execute_action("rover-mock", "deploy_solar_panel", {})
        self.assertTrue(result["ok"])
        self.assertEqual(len(WORLD["solar_panels"]), 1)
        panel = WORLD["solar_panels"][0]
        self.assertEqual(panel["position"], [5, 5])
        self.assertAlmostEqual(panel["battery"], 0.25)
        self.assertFalse(panel["depleted"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["solar_panels_remaining"], 1)

    def test_deploy_max_panels(self):
        execute_action("rover-mock", "deploy_solar_panel", {})
        WORLD["agents"]["rover-mock"]["position"] = [6, 5]
        execute_action("rover-mock", "deploy_solar_panel", {})
        self.assertEqual(len(WORLD["solar_panels"]), 2)
        self.assertEqual(WORLD["agents"]["rover-mock"]["solar_panels_remaining"], 0)
        # Third deploy should fail
        WORLD["agents"]["rover-mock"]["position"] = [7, 5]
        result = execute_action("rover-mock", "deploy_solar_panel", {})
        self.assertFalse(result["ok"])
        self.assertIn("No solar panels remaining", result["error"])

    def test_deploy_duplicate_position_rejected(self):
        execute_action("rover-mock", "deploy_solar_panel", {})
        result = execute_action("rover-mock", "deploy_solar_panel", {})
        self.assertFalse(result["ok"])
        self.assertIn("already deployed", result["error"])

    def test_use_solar_battery_success(self):
        WORLD["agents"]["rover-mock"]["battery"] = 0.50
        execute_action("rover-mock", "deploy_solar_panel", {})
        result = execute_action("rover-mock", "use_solar_battery", {})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_after"], 0.75, places=2)
        self.assertTrue(WORLD["solar_panels"][0]["depleted"])

    def test_use_solar_battery_caps_at_100(self):
        WORLD["agents"]["rover-mock"]["battery"] = 0.90
        execute_action("rover-mock", "deploy_solar_panel", {})
        result = execute_action("rover-mock", "use_solar_battery", {})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_after"], 1.0)

    def test_use_depleted_panel_fails(self):
        WORLD["agents"]["rover-mock"]["battery"] = 0.50
        execute_action("rover-mock", "deploy_solar_panel", {})
        execute_action("rover-mock", "use_solar_battery", {})  # deplete it
        result = execute_action("rover-mock", "use_solar_battery", {})
        self.assertFalse(result["ok"])
        self.assertIn("No active solar panel", result["error"])

    def test_use_at_wrong_position_fails(self):
        execute_action("rover-mock", "deploy_solar_panel", {})
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 0.50
        result = execute_action("rover-mock", "use_solar_battery", {})
        self.assertFalse(result["ok"])
        self.assertIn("No active solar panel", result["error"])

    def test_drone_cannot_deploy(self):
        result = execute_action("drone-mistral", "deploy_solar_panel", {})
        self.assertFalse(result["ok"])
        self.assertIn("Drones cannot", result["error"])

    def test_drone_cannot_use(self):
        # Place a panel manually
        WORLD["solar_panels"].append({
            "position": [0, 0],
            "battery": 0.25,
            "deployed_by": "rover-mock",
            "depleted": False,
        })
        WORLD["agents"]["drone-mistral"]["position"] = [0, 0]
        result = execute_action("drone-mistral", "use_solar_battery", {})
        self.assertFalse(result["ok"])
        self.assertIn("Drones cannot", result["error"])

    def test_snapshot_includes_solar_panels(self):
        execute_action("rover-mock", "deploy_solar_panel", {})
        snap = get_snapshot()
        self.assertIn("solar_panels", snap)
        self.assertEqual(len(snap["solar_panels"]), 1)

    def test_rover_starts_with_panels(self):
        from app.world import MAX_SOLAR_PANELS
        agent = WORLD["agents"]["rover-mock"]
        self.assertEqual(agent.get("solar_panels_remaining"), MAX_SOLAR_PANELS)
