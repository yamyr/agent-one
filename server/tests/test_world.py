import unittest

from app.world import WORLD, move_agent, execute_action, get_snapshot, check_ground
from app.world import check_mission_status, charge_rover
from app.world import BATTERY_COST_MOVE, BATTERY_COST_DIG, BATTERY_COST_PICKUP
from app.world import CHARGE_RATE, REVEAL_RADIUS, GRID_W, GRID_H, AGENT_STARTS
from app.world import assign_mission, _cells_in_radius, record_memory, MEMORY_MAX
from app.world import update_tasks, _direction_hint, reset_world


class TestMoveAgent(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [2, 10]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["randy-rover"]["visited"] = [[2, 10]]

    def test_move_success(self):
        result = move_agent("randy-rover", 3, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [3, 10])

    def test_move_out_of_bounds_negative(self):
        WORLD["agents"]["randy-rover"]["position"] = [0, 10]
        result = move_agent("randy-rover", -1, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Out of bounds", result["error"])

    def test_move_out_of_bounds_over(self):
        WORLD["agents"]["randy-rover"]["position"] = [19, 10]
        result = move_agent("randy-rover", 20, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Out of bounds", result["error"])

    def test_move_too_far(self):
        result = move_agent("randy-rover", 6, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Too far", result["error"])
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [2, 10])

    def test_move_diagonal_rejected(self):
        result = move_agent("randy-rover", 3, 11)
        self.assertFalse(result["ok"])
        self.assertIn("Not a straight line", result["error"])

    def test_move_multi_tile(self):
        result = move_agent("randy-rover", 5, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 3)
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [5, 10])

    def test_move_2_tiles(self):
        result = move_agent("randy-rover", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 2)

    def test_move_already_there(self):
        result = move_agent("randy-rover", 2, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Already at", result["error"])

    def test_move_unknown_agent(self):
        result = move_agent("rover-99", 3, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_move_sequential(self):
        move_agent("randy-rover", 3, 10)
        result = move_agent("randy-rover", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [3, 10])
        self.assertEqual(result["to"], [4, 10])

    def test_move_all_four_directions(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        for tx, ty in [(11, 10), (10, 10), (10, 11), (10, 10)]:
            result = move_agent("randy-rover", tx, ty)
            self.assertTrue(result["ok"])

    def test_get_snapshot_is_copy(self):
        snap = get_snapshot()
        snap["agents"]["randy-rover"]["position"] = [99, 99]
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [2, 10])

    def test_snapshot_has_grid(self):
        snap = get_snapshot()
        self.assertEqual(snap["grid"]["w"], 20)
        self.assertEqual(snap["grid"]["h"], 20)


class TestExecuteAction(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [2, 10]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["randy-rover"]["visited"] = [[2, 10]]

    def test_execute_move_east(self):
        result = execute_action("randy-rover", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [3, 10])

    def test_execute_move_drains_battery(self):
        result = execute_action("randy-rover", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 1.0 - BATTERY_COST_MOVE)

    def test_execute_move_failed_no_drain(self):
        WORLD["agents"]["randy-rover"]["position"] = [0, 10]
        result = execute_action("randy-rover", "move", {"direction": "west"})
        self.assertFalse(result["ok"])
        self.assertEqual(WORLD["agents"]["randy-rover"]["battery"], 1.0)

    def test_execute_move_invalid_direction(self):
        result = execute_action("randy-rover", "move", {"direction": "up"})
        self.assertFalse(result["ok"])
        self.assertIn("Invalid direction", result["error"])

    def test_execute_unknown_action(self):
        result = execute_action("randy-rover", "drill", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])

    def test_execute_unknown_agent(self):
        result = execute_action("rover-99", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_execute_move_all_directions(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        for direction, expected in [
            ("north", [10, 9]),
            ("south", [10, 11]),
            ("east", [11, 10]),
            ("west", [10, 10]),
        ]:
            result = execute_action("randy-rover", "move", {"direction": direction})
            self.assertTrue(result["ok"], f"Failed for direction {direction}")

    def test_execute_move_multi_tile(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        result = execute_action("randy-rover", "move", {"direction": "east", "distance": 3})
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [13, 10])
        self.assertAlmostEqual(
            WORLD["agents"]["randy-rover"]["battery"], 1.0 - BATTERY_COST_MOVE * 3
        )

    def test_execute_move_multi_visits_intermediate(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        execute_action("randy-rover", "move", {"direction": "east", "distance": 3})
        visited = WORLD["agents"]["randy-rover"]["visited"]
        self.assertIn([11, 10], visited)
        self.assertIn([12, 10], visited)
        self.assertIn([13, 10], visited)

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        agent = snap["agents"]["randy-rover"]
        self.assertIn("mission", agent)
        self.assertEqual(agent["mission"]["objective"], "Explore the terrain")
        self.assertEqual(agent["mission"]["plan"], [])


class TestStones(unittest.TestCase):
    def test_stones_generated(self):
        stones = WORLD["stones"]
        self.assertGreaterEqual(len(stones), 5)
        self.assertLessEqual(len(stones), 8)

    def test_guaranteed_core_stones(self):
        core_count = sum(1 for s in WORLD["stones"] if s["type"] == "core")
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
            self.assertEqual(len(stone["position"]), 2)
            self.assertIn(stone["type"], ("core", "basalt"))

    def test_stones_in_bounds(self):
        for stone in WORLD["stones"]:
            x, y = stone["position"]
            self.assertGreaterEqual(x, 0)
            self.assertLess(x, GRID_W)
            self.assertGreaterEqual(y, 0)
            self.assertLess(y, GRID_H)

    def test_stones_avoid_agent_starts(self):
        for stone in WORLD["stones"]:
            pos = tuple(stone["position"])
            self.assertNotIn(pos, AGENT_STARTS)


class TestVisited(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["randy-rover"]["visited"] = [[10, 10]]

    def test_visited_initial(self):
        self.assertEqual(WORLD["agents"]["randy-rover"]["visited"], [[10, 10]])

    def test_move_updates_visited(self):
        execute_action("randy-rover", "move", {"direction": "east"})
        visited = WORLD["agents"]["randy-rover"]["visited"]
        self.assertIn([11, 10], visited)

    def test_visited_no_duplicates(self):
        execute_action("randy-rover", "move", {"direction": "east"})
        execute_action("randy-rover", "move", {"direction": "west"})
        visited = WORLD["agents"]["randy-rover"]["visited"]
        self.assertEqual(visited.count([10, 10]), 1)


class TestCheckGround(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["randy-rover"]["visited"] = [[10, 10]]
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_check_ground_finds_stone(self):
        WORLD["stones"] = [{"position": [10, 10], "type": "core"}]
        result = check_ground("randy-rover")
        self.assertEqual(result["stone"]["type"], "core")
        self.assertFalse(result["stone"]["extracted"])

    def test_check_ground_extracted_stone(self):
        WORLD["stones"] = [{"position": [10, 10], "type": "core", "extracted": True}]
        result = check_ground("randy-rover")
        self.assertEqual(result["stone"]["type"], "core")
        self.assertTrue(result["stone"]["extracted"])

    def test_check_ground_no_stone(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "basalt"}]
        result = check_ground("randy-rover")
        self.assertIsNone(result["stone"])

    def test_move_result_includes_ground(self):
        WORLD["stones"] = []
        result = execute_action("randy-rover", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertIn("ground", result)
        self.assertIsNone(result["ground"]["stone"])


class TestAssignMission(unittest.TestCase):
    def setUp(self):
        self._orig = WORLD["agents"]["randy-rover"]["mission"].copy()

    def tearDown(self):
        WORLD["agents"]["randy-rover"]["mission"] = self._orig

    def test_assign_mission_success(self):
        result = assign_mission("randy-rover", "Go to north edge")
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "randy-rover")
        self.assertEqual(result["objective"], "Go to north edge")
        self.assertEqual(WORLD["agents"]["randy-rover"]["mission"]["objective"], "Go to north edge")

    def test_assign_mission_unknown_agent(self):
        result = assign_mission("rover-99", "Go anywhere")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_assign_mission_preserves_plan(self):
        WORLD["agents"]["randy-rover"]["mission"]["plan"] = ["step1"]
        assign_mission("randy-rover", "New objective")
        self.assertEqual(WORLD["agents"]["randy-rover"]["mission"]["plan"], ["step1"])


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


class TestDig(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [5, 5]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["visited"] = [[5, 5]]
        self._original_stones = WORLD.get("stones", [])
        WORLD["stones"] = [{"position": [5, 5], "type": "core"}]

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_dig_extracts_stone(self):
        result = execute_action("randy-rover", "dig", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"], {"type": "core"})
        self.assertTrue(WORLD["stones"][0]["extracted"])

    def test_dig_drains_battery(self):
        execute_action("randy-rover", "dig", {})
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 1.0 - BATTERY_COST_DIG)

    def test_dig_no_stone(self):
        WORLD["stones"] = []
        result = execute_action("randy-rover", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("No stone", result["error"])

    def test_dig_already_extracted(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "core", "extracted": True}]
        result = execute_action("randy-rover", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("already extracted", result["error"])

    def test_dig_not_enough_battery(self):
        WORLD["agents"]["randy-rover"]["battery"] = 0.01
        result = execute_action("randy-rover", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 0.01)

    def test_dig_failed_no_drain(self):
        WORLD["stones"] = []
        old_battery = WORLD["agents"]["randy-rover"]["battery"]
        execute_action("randy-rover", "dig", {})
        self.assertEqual(WORLD["agents"]["randy-rover"]["battery"], old_battery)


class TestPickup(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [5, 5]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["visited"] = [[5, 5]]
        self._original_stones = WORLD.get("stones", [])
        WORLD["stones"] = [{"position": [5, 5], "type": "core", "extracted": True}]

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_pickup_success(self):
        result = execute_action("randy-rover", "pickup", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"], {"type": "core"})
        self.assertEqual(result["inventory_count"], 1)

    def test_pickup_adds_to_inventory(self):
        execute_action("randy-rover", "pickup", {})
        inv = WORLD["agents"]["randy-rover"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["type"], "core")

    def test_pickup_removes_stone_from_world(self):
        execute_action("randy-rover", "pickup", {})
        self.assertEqual(len(WORLD["stones"]), 0)

    def test_pickup_drains_battery(self):
        execute_action("randy-rover", "pickup", {})
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 1.0 - BATTERY_COST_PICKUP)

    def test_pickup_not_extracted(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "core"}]
        result = execute_action("randy-rover", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("not yet extracted", result["error"])

    def test_pickup_no_stone(self):
        WORLD["stones"] = []
        result = execute_action("randy-rover", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("No stone", result["error"])

    def test_pickup_not_enough_battery(self):
        WORLD["agents"]["randy-rover"]["battery"] = 0.0
        result = execute_action("randy-rover", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_dig_then_pickup(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "basalt"}]
        result = execute_action("randy-rover", "dig", {})
        self.assertTrue(result["ok"])
        result = execute_action("randy-rover", "pickup", {})
        self.assertTrue(result["ok"])
        self.assertEqual(len(WORLD["agents"]["randy-rover"]["inventory"]), 1)
        self.assertEqual(len(WORLD["stones"]), 0)


class TestCharge(unittest.TestCase):
    """Charging is a station-only action via charge_rover()."""

    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [0, 0]
        WORLD["agents"]["randy-rover"]["battery"] = 0.5
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["visited"] = [[0, 0]]
        WORLD["agents"]["randy-rover"]["memory"] = []
        WORLD["agents"]["station"]["position"] = [0, 0]

    def test_charge_rover_success(self):
        result = charge_rover("randy-rover")
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_before"], 0.5)
        self.assertAlmostEqual(result["battery_after"], 0.5 + CHARGE_RATE)

    def test_charge_rover_increases_battery(self):
        charge_rover("randy-rover")
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 0.5 + CHARGE_RATE)

    def test_charge_rover_caps_at_full(self):
        WORLD["agents"]["randy-rover"]["battery"] = 0.95
        charge_rover("randy-rover")
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 1.0)

    def test_charge_rover_already_full(self):
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        result = charge_rover("randy-rover")
        self.assertFalse(result["ok"])
        self.assertIn("already full", result["error"])

    def test_charge_rover_not_at_station(self):
        WORLD["agents"]["randy-rover"]["position"] = [5, 5]
        result = charge_rover("randy-rover")
        self.assertFalse(result["ok"])
        self.assertIn("Not at station", result["error"])

    def test_charge_rover_multiple_times(self):
        WORLD["agents"]["randy-rover"]["battery"] = 0.1
        charge_rover("randy-rover")
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 0.1 + CHARGE_RATE)
        charge_rover("randy-rover")
        self.assertAlmostEqual(WORLD["agents"]["randy-rover"]["battery"], 0.1 + 2 * CHARGE_RATE)

    def test_charge_rover_unknown_agent(self):
        result = charge_rover("rover-99")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_charge_rover_rejects_non_rover(self):
        result = charge_rover("station")
        self.assertFalse(result["ok"])
        self.assertIn("not a rover", result["error"])

    def test_charge_rover_records_memory(self):
        charge_rover("randy-rover")
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_charge_not_available_as_rover_action(self):
        result = execute_action("randy-rover", "charge", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])


class TestFogOfWar(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["visited"] = [[10, 10]]
        WORLD["agents"]["randy-rover"]["revealed"] = [
            [x, y] for x, y in sorted(_cells_in_radius(10, 10, REVEAL_RADIUS))
        ]
        # Give rover-mistral an empty revealed so it doesn't interfere
        WORLD["agents"]["rover-mistral"]["revealed"] = []
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones
        # Restore rover-mistral revealed
        WORLD["agents"]["rover-mistral"]["revealed"] = WORLD["agents"]["rover-mistral"].get(
            "revealed", []
        )

    def test_initial_revealed_cells_count(self):
        revealed = WORLD["agents"]["randy-rover"]["revealed"]
        expected = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertEqual(len(revealed), len(expected))

    def test_initial_revealed_contains_start(self):
        revealed = WORLD["agents"]["randy-rover"]["revealed"]
        self.assertIn([10, 10], revealed)

    def test_initial_revealed_contains_neighbors(self):
        revealed = WORLD["agents"]["randy-rover"]["revealed"]
        for pos in [[10, 9], [10, 11], [9, 10], [11, 10]]:
            self.assertIn(pos, revealed)

    def test_move_expands_revealed(self):
        before = len(WORLD["agents"]["randy-rover"]["revealed"])
        execute_action("randy-rover", "move", {"direction": "east"})
        after = len(WORLD["agents"]["randy-rover"]["revealed"])
        self.assertGreater(after, before)

    def test_move_reveals_new_cells(self):
        execute_action("randy-rover", "move", {"direction": "east"})
        revealed = WORLD["agents"]["randy-rover"]["revealed"]
        # (13, 10) is radius-2 east of new position (11, 10)
        self.assertIn([13, 10], revealed)

    def test_move_no_duplicate_revealed(self):
        execute_action("randy-rover", "move", {"direction": "east"})
        execute_action("randy-rover", "move", {"direction": "west"})
        revealed = WORLD["agents"]["randy-rover"]["revealed"]
        # Check no duplicates
        as_tuples = [tuple(c) for c in revealed]
        self.assertEqual(len(as_tuples), len(set(as_tuples)))

    def test_snapshot_hides_unrevealed_stones(self):
        # Place a stone far from any agent's revealed area
        WORLD["stones"] = [{"position": [19, 19], "type": "core"}]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 0)

    def test_snapshot_shows_revealed_stones(self):
        # Place a stone within randy-rover's revealed area
        WORLD["stones"] = [{"position": [10, 10], "type": "core"}]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["type"], "core")

    def test_snapshot_mixed_visibility(self):
        WORLD["stones"] = [
            {"position": [10, 10], "type": "core"},
            {"position": [19, 19], "type": "basalt"},
        ]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["position"], [10, 10])

    def test_move_reveals_stone(self):
        # Stone beyond reveal radius — not visible at start, visible after moving east
        WORLD["stones"] = [{"position": [16, 10], "type": "basalt"}]
        snap_before = get_snapshot()
        self.assertEqual(len(snap_before["stones"]), 0)
        execute_action("randy-rover", "move", {"direction": "east"})
        snap_after = get_snapshot()
        self.assertEqual(len(snap_after["stones"]), 1)

    def test_cells_in_radius_at_corner(self):
        cells = _cells_in_radius(0, 0, REVEAL_RADIUS)
        # All cells should be in bounds
        for x, y in cells:
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
        # Corner has fewer cells than center
        center_cells = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertLess(len(cells), len(center_cells))

    def test_revealed_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("revealed", snap["agents"]["randy-rover"])


class TestMissionCompletion(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [5, 5]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["visited"] = [[5, 5]]
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
        WORLD["stones"] = [{"position": [5, 5], "type": "core", "extracted": True}]
        execute_action("randy-rover", "pickup", {})
        self.assertEqual(WORLD["mission"]["collected_count"], 1)

    def test_non_target_stone_not_counted(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "basalt", "extracted": True}]
        execute_action("randy-rover", "pickup", {})
        self.assertEqual(WORLD["mission"]["collected_count"], 0)

    def test_pickup_away_from_station_no_success(self):
        """Picking up a target stone away from station should NOT trigger success."""
        WORLD["mission"]["target_count"] = 1
        WORLD["stones"] = [{"position": [5, 5], "type": "core", "extracted": True}]
        result = execute_action("randy-rover", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "running")
        self.assertNotIn("mission", result)
        self.assertEqual(WORLD["mission"]["collected_count"], 1)

    def test_mission_success_on_delivery_to_station(self):
        """Success requires the rover to deliver the stone to the station."""
        WORLD["mission"]["target_count"] = 1
        WORLD["agents"]["randy-rover"]["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["stones"] = [{"position": [0, 0], "type": "core", "extracted": True}]
        result = execute_action("randy-rover", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "success")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "success")

    def test_mission_success_on_move_to_station_with_stone(self):
        """Moving to station while carrying target stone triggers success."""
        WORLD["mission"]["target_count"] = 1
        WORLD["agents"]["randy-rover"]["position"] = [1, 0]
        WORLD["agents"]["randy-rover"]["inventory"] = [{"type": "core"}]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["stones"] = []
        result = execute_action("randy-rover", "move", {"direction": "west"})
        self.assertEqual(WORLD["mission"]["status"], "success")
        self.assertIn("mission", result)

    def test_mission_success_with_two_rovers(self):
        WORLD["mission"]["target_count"] = 2
        WORLD["agents"]["station"]["position"] = [0, 0]
        # Rover-mock picks up one core at station
        WORLD["agents"]["randy-rover"]["position"] = [0, 0]
        WORLD["stones"] = [{"position": [0, 0], "type": "core", "extracted": True}]
        execute_action("randy-rover", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "running")
        # Rover-mistral picks up another core at station
        WORLD["agents"]["rover-mistral"]["position"] = [0, 0]
        WORLD["stones"] = [{"position": [0, 0], "type": "core", "extracted": True}]
        result = execute_action("rover-mistral", "pickup", {})
        self.assertEqual(WORLD["mission"]["status"], "success")
        self.assertEqual(WORLD["mission"]["collected_count"], 2)
        self.assertIn("mission", result)

    def test_mission_failed_all_rovers_depleted(self):
        WORLD["agents"]["randy-rover"]["battery"] = BATTERY_COST_MOVE
        WORLD["agents"]["rover-mistral"]["battery"] = 0.0
        WORLD["agents"]["rover-mistral"]["position"] = [15, 15]
        WORLD["stones"] = []
        # This move will drain randy-rover to 0
        result = execute_action("randy-rover", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(WORLD["mission"]["status"], "failed")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "failed")

    def test_rover_at_station_not_failed(self):
        # Even with 0 battery, rover at station can charge — not failed
        WORLD["agents"]["randy-rover"]["battery"] = BATTERY_COST_MOVE
        WORLD["agents"]["randy-rover"]["position"] = [1, 0]
        WORLD["agents"]["rover-mistral"]["battery"] = 0.0
        WORLD["agents"]["rover-mistral"]["position"] = [0, 0]
        WORLD["agents"]["station"]["position"] = [0, 0]
        WORLD["stones"] = []
        # Move randy-rover, draining to 0 — but rover-mistral is at station
        execute_action("randy-rover", "move", {"direction": "west"})
        self.assertNotEqual(WORLD["mission"]["status"], "failed")

    def test_no_status_change_after_terminal(self):
        WORLD["mission"]["status"] = "success"
        result = check_mission_status()
        self.assertIsNone(result)

    def test_move_does_not_trigger_success(self):
        # Move shouldn't trigger success (no pickup happened)
        WORLD["stones"] = []
        result = execute_action("randy-rover", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertNotIn("mission", result)


class TestMemory(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["randy-rover"]["position"] = [10, 10]
        WORLD["agents"]["randy-rover"]["battery"] = 1.0
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["visited"] = [[10, 10]]
        WORLD["agents"]["randy-rover"]["memory"] = []
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones
        WORLD["agents"]["randy-rover"]["memory"] = []

    def test_move_records_memory(self):
        WORLD["stones"] = []
        execute_action("randy-rover", "move", {"direction": "east"})
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Moved east", mem[0])
        self.assertIn("(11,10)", mem[0])

    def test_move_records_stone_found(self):
        WORLD["stones"] = [{"position": [11, 10], "type": "core"}]
        execute_action("randy-rover", "move", {"direction": "east"})
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertIn("core", mem[0])

    def test_dig_records_memory(self):
        WORLD["stones"] = [{"position": [10, 10], "type": "basalt"}]
        execute_action("randy-rover", "dig", {})
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Dug out basalt", mem[0])

    def test_pickup_records_memory(self):
        WORLD["stones"] = [{"position": [10, 10], "type": "core", "extracted": True}]
        execute_action("randy-rover", "pickup", {})
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Picked up core", mem[0])
        self.assertIn("inventory=1", mem[0])

    def test_charge_records_memory(self):
        WORLD["agents"]["randy-rover"]["position"] = [0, 0]
        WORLD["agents"]["randy-rover"]["battery"] = 0.5
        charge_rover("randy-rover")
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_failed_action_records_memory(self):
        WORLD["stones"] = []
        execute_action("randy-rover", "dig", {})
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Failed dig", mem[0])

    def test_memory_capped_at_max(self):
        for i in range(MEMORY_MAX + 5):
            record_memory("randy-rover", f"entry {i}")
        mem = WORLD["agents"]["randy-rover"]["memory"]
        self.assertEqual(len(mem), MEMORY_MAX)
        self.assertEqual(mem[0], f"entry {5}")
        self.assertEqual(mem[-1], f"entry {MEMORY_MAX + 4}")

    def test_memory_in_snapshot(self):
        record_memory("randy-rover", "test entry")
        snap = get_snapshot()
        self.assertIn("memory", snap["agents"]["randy-rover"])
        self.assertEqual(snap["agents"]["randy-rover"]["memory"], ["test entry"])

    def test_record_memory_unknown_agent(self):
        # Should not raise
        record_memory("nonexistent", "noop")


class TestDirectionHint(unittest.TestCase):
    def test_north(self):
        self.assertEqual(_direction_hint(0, -3), "north")

    def test_south_east(self):
        self.assertEqual(_direction_hint(2, 5), "south, east")

    def test_west(self):
        self.assertEqual(_direction_hint(-1, 0), "west")

    def test_here(self):
        self.assertEqual(_direction_hint(0, 0), "here")


class TestUpdateTasks(unittest.TestCase):
    def setUp(self):
        self._orig_pos = WORLD["agents"]["randy-rover"]["position"][:]
        self._orig_inv = WORLD["agents"]["randy-rover"].get("inventory", [])[:]
        self._orig_stones = WORLD.get("stones", [])[:]
        self._orig_tasks = WORLD["agents"]["randy-rover"].get("tasks", [])[:]
        self._orig_discovered = WORLD["agents"]["randy-rover"].get("discovered_stones", [])[:]
        WORLD["agents"]["randy-rover"]["position"] = [5, 5]
        WORLD["agents"]["randy-rover"]["inventory"] = []
        WORLD["agents"]["randy-rover"]["tasks"] = []
        WORLD["agents"]["randy-rover"]["discovered_stones"] = []

    def tearDown(self):
        WORLD["agents"]["randy-rover"]["position"] = self._orig_pos
        WORLD["agents"]["randy-rover"]["inventory"] = self._orig_inv
        WORLD["stones"] = self._orig_stones
        WORLD["agents"]["randy-rover"]["tasks"] = self._orig_tasks
        WORLD["agents"]["randy-rover"]["discovered_stones"] = self._orig_discovered

    def test_explore_when_no_stones(self):
        WORLD["stones"] = []
        update_tasks("randy-rover")
        tasks = WORLD["agents"]["randy-rover"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Explore", tasks[0])

    def test_dig_when_stone_buried(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "core"}]
        update_tasks("randy-rover")
        tasks = WORLD["agents"]["randy-rover"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Dig", tasks[0])

    def test_pickup_when_stone_extracted(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "core", "extracted": True}]
        update_tasks("randy-rover")
        tasks = WORLD["agents"]["randy-rover"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Pick up", tasks[0])

    def test_navigate_to_discovered_stone(self):
        WORLD["stones"] = [{"position": [8, 5], "type": "core"}]
        agent = WORLD["agents"]["randy-rover"]
        agent["discovered_stones"] = [[8, 5]]
        update_tasks("randy-rover")
        tasks = WORLD["agents"]["randy-rover"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Navigate", tasks[0])
        self.assertIn("east", tasks[0])

    def test_no_navigate_to_undiscovered_stone(self):
        WORLD["stones"] = [{"position": [8, 5], "type": "core"}]
        agent = WORLD["agents"]["randy-rover"]
        agent["discovered_stones"] = []
        # Stone is on a revealed tile but not discovered
        if [8, 5] not in agent.get("revealed", []):
            agent.setdefault("revealed", []).append([8, 5])
        update_tasks("randy-rover")
        tasks = WORLD["agents"]["randy-rover"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Explore", tasks[0])

    def test_return_to_station_when_has_target(self):
        WORLD["agents"]["randy-rover"]["inventory"] = [{"type": "core"}]
        update_tasks("randy-rover")
        tasks = WORLD["agents"]["randy-rover"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Return to station", tasks[0])


class TestResetWorld(unittest.TestCase):

    def test_reset_restores_positions(self):
        WORLD["agents"]["randy-rover"]["position"] = [15, 15]
        WORLD["agents"]["randy-rover"]["battery"] = 0.1
        WORLD["mission"]["status"] = "success"
        reset_world()
        self.assertEqual(WORLD["agents"]["randy-rover"]["position"], [2, 10])
        self.assertEqual(WORLD["agents"]["randy-rover"]["battery"], 1.0)
        self.assertEqual(WORLD["mission"]["status"], "running")

    def test_reset_clears_inventory_and_memory(self):
        WORLD["agents"]["randy-rover"]["inventory"] = [{"type": "core"}]
        WORLD["agents"]["randy-rover"]["memory"] = ["something"]
        reset_world()
        self.assertEqual(WORLD["agents"]["randy-rover"]["inventory"], [])
        self.assertEqual(WORLD["agents"]["randy-rover"]["memory"], [])

    def test_reset_regenerates_stones(self):
        WORLD["stones"] = []
        reset_world()
        self.assertGreaterEqual(len(WORLD["stones"]), 5)
