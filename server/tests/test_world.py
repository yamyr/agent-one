import random
import unittest

from app.world import world, GRID_W, GRID_H, move_agent, execute_action, get_snapshot, check_ground
from app.world import check_mission_status, charge_rover, charge_agent
from app.world import BATTERY_COST_MOVE, BATTERY_COST_DIG
from app.world import BATTERY_COST_ANALYZE
from app.world import BATTERY_COST_SCAN, BATTERY_COST_MOVE_DRONE, BATTERY_COST_NOTIFY
from app.world import CHARGE_RATE, REVEAL_RADIUS, ROVER_REVEAL_RADIUS, DRONE_REVEAL_RADIUS
from app.world import AGENT_STARTS
from app.world import abort_mission, all_agents_at_station
from app.world import assign_mission, _cells_in_radius, record_memory, MEMORY_MAX
from app.world import update_tasks, direction_hint
from app.world import set_agent_model, set_agent_last_context, set_pending_commands
from app.world import observe_rover, observe_station
from app.world import VEIN_GRADES, VEIN_WEIGHTS, VEIN_QUANTITY_RANGES, TARGET_QUANTITY
from app.world import MAX_INVENTORY_ROVER
from app.models import RoverContext, StationContext, StoneInfo


def _make_vein(pos, grade="high", quantity=200, analyzed=False):
    """Helper to build a vein dict for tests."""
    return {
        "position": list(pos),
        "type": "basalt_vein" if analyzed else "unknown",
        "_true_type": "basalt_vein",
        "grade": grade if analyzed else "unknown",
        "_true_grade": grade,
        "quantity": quantity if analyzed else 0,
        "_true_quantity": quantity,
        "analyzed": analyzed,
    }


class TestMoveAgent(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [2, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[2, 10]]

    def test_move_success(self):
        result = move_agent("rover-mistral", 3, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [3, 10])

    def test_move_negative_coords_allowed(self):
        """Infinite grid: negative coordinates are valid."""
        world.state["agents"]["rover-mistral"]["position"] = [0, 10]
        result = move_agent("rover-mistral", -1, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["to"], [-1, 10])

    def test_move_beyond_old_bounds_allowed(self):
        """Infinite grid: moving beyond old 20x20 bounds is valid."""
        world.state["agents"]["rover-mistral"]["position"] = [19, 10]
        result = move_agent("rover-mistral", 20, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["to"], [20, 10])

    def test_move_too_far(self):
        result = move_agent("rover-mistral", 6, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Too far", result["error"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_move_diagonal_rejected(self):
        result = move_agent("rover-mistral", 3, 11)
        self.assertFalse(result["ok"])
        self.assertIn("Not a straight line", result["error"])

    def test_move_multi_tile(self):
        result = move_agent("rover-mistral", 5, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 3)
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [5, 10])

    def test_move_2_tiles(self):
        result = move_agent("rover-mistral", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 2)

    def test_move_already_there(self):
        result = move_agent("rover-mistral", 2, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Already at", result["error"])

    def test_move_unknown_agent(self):
        result = move_agent("rover-99", 3, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_move_sequential(self):
        move_agent("rover-mistral", 3, 10)
        result = move_agent("rover-mistral", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [3, 10])
        self.assertEqual(result["to"], [4, 10])

    def test_move_all_four_directions(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        for tx, ty in [(11, 10), (10, 10), (10, 11), (10, 10)]:
            result = move_agent("rover-mistral", tx, ty)
            self.assertTrue(result["ok"])

    def test_get_snapshot_is_copy(self):
        snap = get_snapshot()
        snap["agents"]["rover-mistral"]["position"] = [99, 99]
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_snapshot_has_grid(self):
        snap = get_snapshot()
        self.assertEqual(snap["grid"]["w"], 20)
        self.assertEqual(snap["grid"]["h"], 20)


class TestExecuteAction(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [2, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[2, 10]]

    def test_execute_move_east(self):
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [3, 10])

    def test_execute_move_drains_battery(self):
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_MOVE
        )

    def test_execute_move_negative_ok(self):
        """Infinite grid: moving to negative coords succeeds."""
        world.state["agents"]["rover-mistral"]["position"] = [0, 10]
        result = execute_action("rover-mistral", "move", {"direction": "west"})
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [-1, 10])

    def test_execute_move_invalid_direction(self):
        result = execute_action("rover-mistral", "move", {"direction": "up"})
        self.assertFalse(result["ok"])
        self.assertIn("Invalid direction", result["error"])

    def test_execute_unknown_action(self):
        result = execute_action("rover-mistral", "drill", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])

    def test_execute_unknown_agent(self):
        result = execute_action("rover-99", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_execute_move_all_directions(self):
        """North = +Y, South = -Y with flipped coordinate system."""
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        for direction, expected in [
            ("north", [10, 11]),
            ("south", [10, 9]),
            ("east", [11, 10]),
            ("west", [10, 10]),
        ]:
            result = execute_action("rover-mistral", "move", {"direction": direction})
            self.assertTrue(result["ok"], f"Failed for direction {direction}")

    def test_execute_move_multi_tile(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        result = execute_action("rover-mistral", "move", {"direction": "east", "distance": 3})
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [13, 10])
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_MOVE * 3
        )

    def test_execute_move_multi_visits_intermediate(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        execute_action("rover-mistral", "move", {"direction": "east", "distance": 3})
        visited = world.state["agents"]["rover-mistral"]["visited"]
        self.assertIn([11, 10], visited)
        self.assertIn([12, 10], visited)
        self.assertIn([13, 10], visited)

    def test_execute_move_no_battery(self):
        """Move should fail when battery is too low."""
        world.state["agents"]["rover-mistral"]["battery"] = 0.0
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_execute_move_insufficient_battery_multi(self):
        """Multi-tile move should fail when battery < cost for full distance."""
        world.state["agents"]["rover-mistral"]["battery"] = (
            BATTERY_COST_MOVE * 2
        )  # enough for ~1-2 tiles, not 3
        result = execute_action("rover-mistral", "move", {"direction": "east", "distance": 3})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        agent = snap["agents"]["rover-mistral"]
        self.assertIn("mission", agent)
        self.assertEqual(agent["mission"]["objective"], "Explore the terrain")
        self.assertEqual(agent["mission"]["plan"], [])


class TestStones(unittest.TestCase):
    def test_stones_generated(self):
        """With chunk system, initial chunks generate multiple veins."""
        stones = world.state["stones"]
        self.assertGreaterEqual(len(stones), 1)

    def test_all_veins_are_basalt(self):
        """All generated veins should have _true_type basalt_vein."""
        for s in world.state["stones"]:
            self.assertEqual(s["_true_type"], "basalt_vein")

    def test_veins_have_valid_grades(self):
        """Every vein should have a valid _true_grade."""
        for s in world.state["stones"]:
            self.assertIn(s["_true_grade"], VEIN_GRADES)

    def test_veins_quantity_in_range(self):
        """Every vein's _true_quantity should fall within the range for its grade."""
        for s in world.state["stones"]:
            grade = s["_true_grade"]
            lo, hi = VEIN_QUANTITY_RANGES[grade]
            self.assertGreaterEqual(s["_true_quantity"], lo)
            self.assertLessEqual(s["_true_quantity"], hi)

    def test_stones_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("stones", snap)
        self.assertLessEqual(len(snap["stones"]), len(world.state["stones"]))

    def test_stone_shape(self):
        for stone in world.state["stones"]:
            self.assertIn("position", stone)
            self.assertIn("type", stone)
            self.assertIn("_true_type", stone)
            self.assertIn("grade", stone)
            self.assertIn("_true_grade", stone)
            self.assertIn("quantity", stone)
            self.assertIn("_true_quantity", stone)
            self.assertIn("analyzed", stone)
            self.assertNotIn("extracted", stone)
            self.assertEqual(len(stone["position"]), 2)
            self.assertEqual(stone["_true_type"], "basalt_vein")
            self.assertEqual(stone["type"], "unknown")
            self.assertEqual(stone["grade"], "unknown")
            self.assertEqual(stone["quantity"], 0)
            self.assertFalse(stone["analyzed"])

    def test_stones_have_valid_positions(self):
        """Veins should have integer coordinate positions (no bounds requirement)."""
        for stone in world.state["stones"]:
            x, y = stone["position"]
            self.assertIsInstance(x, int)
            self.assertIsInstance(y, int)

    def test_stones_avoid_agent_starts(self):
        for stone in world.state["stones"]:
            pos = tuple(stone["position"])
            self.assertNotIn(pos, AGENT_STARTS)

    def test_snapshot_strips_hidden_fields(self):
        snap = get_snapshot()
        for stone in snap["stones"]:
            self.assertNotIn("_true_type", stone)
            self.assertNotIn("_true_grade", stone)
            self.assertNotIn("_true_quantity", stone)


class TestVisited(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]

    def test_visited_initial(self):
        self.assertEqual(world.state["agents"]["rover-mistral"]["visited"], [[10, 10]])

    def test_move_updates_visited(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        visited = world.state["agents"]["rover-mistral"]["visited"]
        self.assertIn([11, 10], visited)

    def test_visited_no_duplicates(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        execute_action("rover-mistral", "move", {"direction": "west"})
        visited = world.state["agents"]["rover-mistral"]["visited"]
        self.assertEqual(visited.count([10, 10]), 1)


class TestCheckGround(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_check_ground_finds_stone(self):
        world.state["stones"] = [_make_vein([10, 10])]
        result = check_ground("rover-mistral")
        self.assertEqual(result["stone"]["type"], "unknown")
        self.assertEqual(result["stone"]["grade"], "unknown")

    def test_check_ground_no_stone(self):
        world.state["stones"] = [_make_vein([5, 5])]
        result = check_ground("rover-mistral")
        self.assertIsNone(result["stone"])

    def test_move_result_includes_ground(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertIn("ground", result)
        self.assertIsNone(result["ground"]["stone"])


class TestAssignMission(unittest.TestCase):
    def setUp(self):
        self._orig = world.state["agents"]["rover-mistral"]["mission"].copy()

    def tearDown(self):
        world.state["agents"]["rover-mistral"]["mission"] = self._orig

    def test_assign_mission_success(self):
        result = assign_mission("rover-mistral", "Go to north edge")
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "rover-mistral")
        self.assertEqual(result["objective"], "Go to north edge")
        self.assertEqual(
            world.state["agents"]["rover-mistral"]["mission"]["objective"], "Go to north edge"
        )

    def test_assign_mission_unknown_agent(self):
        result = assign_mission("rover-99", "Go anywhere")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_assign_mission_preserves_plan(self):
        world.state["agents"]["rover-mistral"]["mission"]["plan"] = ["step1"]
        assign_mission("rover-mistral", "New objective")
        self.assertEqual(world.state["agents"]["rover-mistral"]["mission"]["plan"], ["step1"])


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
    """Test the analyze action that reveals hidden vein grade and quantity."""

    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = [_make_vein([5, 5], grade="rich", quantity=500)]

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_analyze_reveals_type_grade_quantity(self):
        result = execute_action("rover-mistral", "analyze", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "basalt_vein")
        self.assertEqual(result["stone"]["grade"], "rich")
        self.assertEqual(result["stone"]["quantity"], 500)
        stone = world.state["stones"][0]
        self.assertTrue(stone["analyzed"])
        self.assertEqual(stone["type"], "basalt_vein")
        self.assertEqual(stone["grade"], "rich")
        self.assertEqual(stone["quantity"], 500)

    def test_analyze_drains_battery(self):
        execute_action("rover-mistral", "analyze", {})
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_ANALYZE
        )

    def test_analyze_no_stone(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("No vein", result["error"])

    def test_analyze_already_analyzed(self):
        world.state["stones"] = [_make_vein([5, 5], grade="low", quantity=30, analyzed=True)]
        result = execute_action("rover-mistral", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("already analyzed", result["error"])

    def test_analyze_unknown_agent(self):
        result = execute_action("rover-99", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_analyze_not_enough_battery(self):
        world.state["agents"]["rover-mistral"]["battery"] = BATTERY_COST_ANALYZE * 0.5
        result = execute_action("rover-mistral", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_analyze_records_memory(self):
        execute_action("rover-mistral", "analyze", {})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Analyzed", mem[0])
        self.assertIn("grade=rich", mem[0])
        self.assertIn("qty=500", mem[0])


class TestDig(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_dig_collects_stone(self):
        result = execute_action("rover-mistral", "dig", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "basalt_vein")
        self.assertEqual(result["stone"]["grade"], "high")
        self.assertEqual(result["stone"]["quantity"], 200)
        self.assertEqual(result["inventory_count"], 1)
        # Stone removed from world, added to inventory
        self.assertEqual(len(world.state["stones"]), 0)
        inv = world.state["agents"]["rover-mistral"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["grade"], "high")
        self.assertEqual(inv[0]["quantity"], 200)

    def test_dig_drains_battery(self):
        execute_action("rover-mistral", "dig", {})
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_DIG
        )

    def test_dig_no_stone(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("No vein", result["error"])

    def test_dig_not_enough_battery(self):
        world.state["agents"]["rover-mistral"]["battery"] = BATTERY_COST_DIG * 0.5
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], BATTERY_COST_DIG * 0.5
        )

    def test_dig_failed_no_drain(self):
        world.state["stones"] = []
        old_battery = world.state["agents"]["rover-mistral"]["battery"]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["agents"]["rover-mistral"]["battery"], old_battery)

    def test_dig_requires_analyze(self):
        """Dig should fail if vein is not yet analyzed."""
        world.state["stones"] = [_make_vein([5, 5])]
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("not yet analyzed", result["error"])

    def test_dig_inventory_full(self):
        """Dig should fail when inventory already has MAX_INVENTORY_ROVER veins."""
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "low", "quantity": 50}
            for _ in range(MAX_INVENTORY_ROVER)
        ]
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("Inventory full", result["error"])


class TestAnalyzeDigWorkflow(unittest.TestCase):
    """Test the merged analyze → dig workflow (dig now collects into inventory)."""

    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_analyze_dig_workflow(self):
        """Full workflow: analyze → dig (collects into inventory)."""
        world.state["stones"] = [_make_vein([5, 5], grade="pristine", quantity=900)]
        result = execute_action("rover-mistral", "analyze", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "basalt_vein")
        self.assertEqual(result["stone"]["grade"], "pristine")
        self.assertEqual(result["stone"]["quantity"], 900)
        result = execute_action("rover-mistral", "dig", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["inventory_count"], 1)
        inv = world.state["agents"]["rover-mistral"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["quantity"], 900)
        self.assertEqual(len(world.state["stones"]), 0)

    def test_dig_removes_stone_from_world(self):
        world.state["stones"] = [_make_vein([5, 5], grade="rich", quantity=400, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(len(world.state["stones"]), 0)

    def test_dig_adds_to_inventory_with_grade_and_quantity(self):
        world.state["stones"] = [_make_vein([5, 5], grade="rich", quantity=400, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        inv = world.state["agents"]["rover-mistral"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["type"], "basalt_vein")
        self.assertEqual(inv[0]["grade"], "rich")
        self.assertEqual(inv[0]["quantity"], 400)

    def test_pickup_action_no_longer_exists(self):
        """Pickup action should return 'Unknown action' since it was removed."""
        world.state["stones"] = [_make_vein([5, 5], grade="low", quantity=30, analyzed=True)]
        result = execute_action("rover-mistral", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])


class TestCharge(unittest.TestCase):
    """Charging is a station-only action via charge_rover()."""

    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["battery"] = 0.5
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        world.state["agents"]["station"]["position"] = [0, 0]

    def test_charge_rover_success(self):
        result = charge_rover("rover-mistral")
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_before"], 0.5)
        self.assertAlmostEqual(result["battery_after"], 0.5 + CHARGE_RATE)

    def test_charge_rover_increases_battery(self):
        charge_rover("rover-mistral")
        self.assertAlmostEqual(world.state["agents"]["rover-mistral"]["battery"], 0.5 + CHARGE_RATE)

    def test_charge_rover_caps_at_full(self):
        world.state["agents"]["rover-mistral"]["battery"] = 0.95
        charge_rover("rover-mistral")
        self.assertAlmostEqual(world.state["agents"]["rover-mistral"]["battery"], 1.0)

    def test_charge_rover_already_full(self):
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        result = charge_rover("rover-mistral")
        self.assertFalse(result["ok"])
        self.assertIn("already full", result["error"])

    def test_charge_rover_not_at_station(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        result = charge_rover("rover-mistral")
        self.assertFalse(result["ok"])
        self.assertIn("Not at station", result["error"])

    def test_charge_rover_multiple_times(self):
        world.state["agents"]["rover-mistral"]["battery"] = 0.1
        charge_rover("rover-mistral")
        self.assertAlmostEqual(world.state["agents"]["rover-mistral"]["battery"], 0.1 + CHARGE_RATE)
        charge_rover("rover-mistral")
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 0.1 + 2 * CHARGE_RATE
        )

    def test_charge_rover_unknown_agent(self):
        result = charge_rover("rover-99")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_charge_agent_rejects_station(self):
        result = charge_agent("station")
        self.assertFalse(result["ok"])
        self.assertIn("is a station", result["error"])

    def test_charge_rover_records_memory(self):
        charge_rover("rover-mistral")
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_charge_not_available_as_rover_action(self):
        result = execute_action("rover-mistral", "charge", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])


class TestFogOfWar(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        world.state["agents"]["rover-mistral"]["revealed"] = [
            [x, y] for x, y in sorted(_cells_in_radius(10, 10, REVEAL_RADIUS))
        ]
        # Give drone an empty revealed so it doesn't interfere
        if "drone-mistral" in world.state["agents"]:
            self._original_drone_revealed = world.state["agents"]["drone-mistral"].get(
                "revealed", []
            )
            world.state["agents"]["drone-mistral"]["revealed"] = []
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones
        # Restore rover-mistral revealed
        world.state["agents"]["rover-mistral"]["revealed"] = world.state["agents"][
            "rover-mistral"
        ].get("revealed", [])
        if "drone-mistral" in world.state["agents"]:
            world.state["agents"]["drone-mistral"]["revealed"] = self._original_drone_revealed

    def test_initial_revealed_cells_count(self):
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        expected = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertEqual(len(revealed), len(expected))

    def test_initial_revealed_contains_start(self):
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        self.assertIn([10, 10], revealed)

    def test_initial_revealed_contains_neighbors(self):
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        for pos in [[10, 9], [10, 11], [9, 10], [11, 10]]:
            self.assertIn(pos, revealed)

    def test_move_expands_revealed(self):
        before = len(world.state["agents"]["rover-mistral"]["revealed"])
        execute_action("rover-mistral", "move", {"direction": "east"})
        after = len(world.state["agents"]["rover-mistral"]["revealed"])
        self.assertGreater(after, before)

    def test_move_reveals_new_cells(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        # (13, 10) is radius-2 east of new position (11, 10)
        self.assertIn([13, 10], revealed)

    def test_move_no_duplicate_revealed(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        execute_action("rover-mistral", "move", {"direction": "west"})
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        # Check no duplicates
        as_tuples = [tuple(c) for c in revealed]
        self.assertEqual(len(as_tuples), len(set(as_tuples)))

    def test_snapshot_hides_unrevealed_stones(self):
        world.state["stones"] = [_make_vein([19, 19])]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 0)

    def test_snapshot_shows_revealed_stones(self):
        world.state["stones"] = [_make_vein([10, 10])]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["type"], "unknown")

    def test_snapshot_mixed_visibility(self):
        world.state["stones"] = [_make_vein([10, 10]), _make_vein([19, 19])]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["position"], [10, 10])

    def test_move_reveals_stone(self):
        world.state["stones"] = [_make_vein([14, 10])]
        snap_before = get_snapshot()
        self.assertEqual(len(snap_before["stones"]), 0)
        execute_action("rover-mistral", "move", {"direction": "east"})
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
        self.assertIn("revealed", snap["agents"]["rover-mistral"])


class TestMissionCompletion(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        self._original_stones = world.state.get("stones", [])
        self._original_mission = world.state["mission"].copy()
        world.state["mission"]["status"] = "running"
        world.state["mission"]["collected_quantity"] = 0

    def tearDown(self):
        world.state["stones"] = self._original_stones
        world.state["mission"] = self._original_mission

    def test_mission_in_world(self):
        self.assertIn("mission", world.state)
        self.assertEqual(world.state["mission"]["status"], "running")
        self.assertEqual(world.state["mission"]["target_type"], "basalt_vein")
        self.assertEqual(world.state["mission"]["target_quantity"], TARGET_QUANTITY)

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("mission", snap)
        self.assertEqual(snap["mission"]["status"], "running")

    def test_collected_quantity_updates_on_dig(self):
        """Dig away from station: vein is in transit, not yet collected."""
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["collected_quantity"], 0)
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 200)

    def test_dig_away_from_station_no_success(self):
        """Digging a vein away from station should NOT trigger success."""
        world.state["mission"]["target_quantity"] = 100
        world.state["stones"] = [_make_vein([5, 5], grade="pristine", quantity=900, analyzed=True)]
        result = execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "running")
        self.assertNotIn("mission", result)
        self.assertEqual(world.state["mission"]["collected_quantity"], 0)
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 900)

    def test_mission_success_on_delivery_to_station(self):
        """Success requires the rover to deliver basalt to the station."""
        world.state["mission"]["target_quantity"] = 100
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="high", quantity=200, analyzed=True)]
        result = execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "success")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "success")

    def test_mission_success_on_move_to_station_with_basalt(self):
        """Moving to station while carrying enough basalt triggers success."""
        world.state["mission"]["target_quantity"] = 100
        world.state["agents"]["rover-mistral"]["position"] = [1, 0]
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "rich", "quantity": 150}
        ]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = []
        result = execute_action("rover-mistral", "move", {"direction": "west"})
        self.assertEqual(world.state["mission"]["status"], "success")
        self.assertIn("mission", result)

    def test_mission_success_with_multiple_digs(self):
        """Multiple digs contributing basalt to reach target_quantity."""
        world.state["mission"]["target_quantity"] = 300
        world.state["agents"]["station"]["position"] = [0, 0]
        # First dig: 200 units at station
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="high", quantity=200, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "running")
        # Rover-mistral digs another 200 at station — total 400 >= 300
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="high", quantity=200, analyzed=True)]
        result = execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "success")
        self.assertEqual(world.state["mission"]["collected_quantity"], 400)
        self.assertIn("mission", result)

    def test_mission_failed_all_rovers_depleted(self):
        world.state["agents"]["rover-mistral"]["battery"] = BATTERY_COST_MOVE
        world.state["agents"]["rover-mistral"]["position"] = [15, 15]
        world.state["stones"] = []
        # This move will drain rover-mistral to 0
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["mission"]["status"], "failed")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "failed")

    def test_rover_at_station_not_failed(self):
        # Even with 0 battery, rover at station can charge — not failed
        world.state["agents"]["rover-mistral"]["battery"] = 0.0
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = []
        # Rover at station with 0 battery — should not be failed
        result = check_mission_status()
        self.assertIsNone(result)
        self.assertNotEqual(world.state["mission"]["status"], "failed")

    def test_no_status_change_after_terminal(self):
        world.state["mission"]["status"] = "success"
        result = check_mission_status()
        self.assertIsNone(result)

    def test_move_does_not_trigger_success(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertNotIn("mission", result)

    def test_partial_delivery_not_enough(self):
        """Delivering less than target_quantity should not trigger success."""
        world.state["mission"]["target_quantity"] = 500
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="medium", quantity=100, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "running")
        self.assertEqual(world.state["mission"]["collected_quantity"], 100)


class TestMemory(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones
        world.state["agents"]["rover-mistral"]["memory"] = []

    def test_move_records_memory(self):
        world.state["stones"] = []
        execute_action("rover-mistral", "move", {"direction": "east"})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Moved east", mem[0])
        self.assertIn("(11,10)", mem[0])

    def test_move_records_stone_found(self):
        world.state["stones"] = [_make_vein([11, 10])]
        execute_action("rover-mistral", "move", {"direction": "east"})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertIn("unknown", mem[0])

    def test_dig_records_memory(self):
        world.state["stones"] = [_make_vein([10, 10], grade="medium", quantity=80, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Dug and collected medium", mem[0])
        self.assertIn("qty=80", mem[0])
        self.assertIn("inventory=1", mem[0])

    def test_charge_records_memory(self):
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["battery"] = 0.5
        charge_rover("rover-mistral")
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_failed_action_records_memory(self):
        world.state["stones"] = []
        execute_action("rover-mistral", "dig", {})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Failed dig", mem[0])

    def test_memory_capped_at_max(self):
        for i in range(MEMORY_MAX + 5):
            record_memory("rover-mistral", f"entry {i}")
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), MEMORY_MAX)
        self.assertEqual(mem[0], f"entry {5}")
        self.assertEqual(mem[-1], f"entry {MEMORY_MAX + 4}")

    def test_memory_in_snapshot(self):
        record_memory("rover-mistral", "test entry")
        snap = get_snapshot()
        self.assertIn("memory", snap["agents"]["rover-mistral"])
        self.assertEqual(snap["agents"]["rover-mistral"]["memory"], ["test entry"])

    def test_record_memory_unknown_agent(self):
        # Should not raise
        record_memory("nonexistent", "noop")


class TestDirectionHint(unittest.TestCase):
    """Direction hints use math convention: north = +Y, south = -Y."""

    def test_north(self):
        self.assertEqual(direction_hint(0, 3), "north")

    def test_south(self):
        self.assertEqual(direction_hint(0, -3), "south")

    def test_south_east(self):
        self.assertEqual(direction_hint(2, -5), "south, east")

    def test_north_east(self):
        self.assertEqual(direction_hint(2, 5), "north, east")

    def test_west(self):
        self.assertEqual(direction_hint(-1, 0), "west")

    def test_here(self):
        self.assertEqual(direction_hint(0, 0), "here")


class TestUpdateTasks(unittest.TestCase):
    def setUp(self):
        self._orig_pos = world.state["agents"]["rover-mistral"]["position"][:]
        self._orig_inv = world.state["agents"]["rover-mistral"].get("inventory", [])[:]
        self._orig_stones = world.state.get("stones", [])[:]
        self._orig_tasks = world.state["agents"]["rover-mistral"].get("tasks", [])[:]
        self._orig_mission = world.state["mission"].copy()
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["tasks"] = []
        world.state["mission"]["status"] = "running"
        world.state["mission"]["collected_quantity"] = 0

    def tearDown(self):
        world.state["agents"]["rover-mistral"]["position"] = self._orig_pos
        world.state["agents"]["rover-mistral"]["inventory"] = self._orig_inv
        world.state["stones"] = self._orig_stones
        world.state["agents"]["rover-mistral"]["tasks"] = self._orig_tasks
        world.state["mission"] = self._orig_mission

    def test_explore_when_no_stones(self):
        world.state["stones"] = []
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Explore", tasks[0])

    def test_analyze_when_stone_unanalyzed(self):
        world.state["stones"] = [_make_vein([5, 5])]
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertTrue(any("Analyze" in t for t in tasks))

    def test_dig_when_stone_analyzed(self):
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertTrue(any("Dig" in t for t in tasks))

    def test_navigate_to_known_stone(self):
        world.state["stones"] = [_make_vein([8, 5])]
        agent = world.state["agents"]["rover-mistral"]
        if [8, 5] not in agent.get("revealed", []):
            agent.setdefault("revealed", []).append([8, 5])
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("Navigate", tasks[0])
        self.assertIn("east", tasks[0])

    def test_goal_present_when_carrying_basalt(self):
        """Tasks should show an actionable goal even when inventory has items."""
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "high", "quantity": 200}
        ]
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertTrue(len(tasks) >= 1)
        self.assertFalse(any("Inventory" in t for t in tasks))


class TestObserveRover(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 0.75
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0], [5, 5]]
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["memory"] = ["moved east"]
        world.state["agents"]["rover-mistral"]["tasks"] = []
        world.state["stones"] = []

    def test_returns_rover_context_type(self):
        ctx = observe_rover("rover-mistral")
        self.assertIsInstance(ctx, RoverContext)

    def test_agent_state_fields(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.agent.position, [5, 5])
        self.assertAlmostEqual(ctx.agent.battery, 0.75)
        self.assertEqual(ctx.agent.mission.objective, "Explore")
        self.assertEqual(ctx.agent.memory, ["moved east"])
        self.assertEqual(ctx.agent.visited_count, 2)

    def test_world_view_fields(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.world.grid_w, GRID_W)
        self.assertEqual(ctx.world.grid_h, GRID_H)
        self.assertEqual(ctx.world.station_position, [0, 0])

    def test_unvisited_dirs(self):
        ctx = observe_rover("rover-mistral")
        # (5,5) with visited={(0,0),(5,5)} — all 4 neighbors are unvisited
        for d in ["north", "south", "east", "west"]:
            self.assertIn(d, ctx.computed.unvisited_dirs)

    def test_unvisited_dirs_excludes_visited(self):
        world.state["agents"]["rover-mistral"]["visited"].append([5, 6])
        ctx = observe_rover("rover-mistral")
        self.assertNotIn("north", ctx.computed.unvisited_dirs)

    def test_stone_line_none(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.computed.stone_line, "none")
        self.assertIsNone(ctx.computed.stone_here)

    def test_stone_line_unknown(self):
        world.state["stones"] = [_make_vein([5, 5])]
        ctx = observe_rover("rover-mistral")
        self.assertIn("unknown", ctx.computed.stone_line)
        self.assertIsNotNone(ctx.computed.stone_here)
        self.assertIsInstance(ctx.computed.stone_here, StoneInfo)

    def test_stone_line_analyzed(self):
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]
        ctx = observe_rover("rover-mistral")
        self.assertIn("needs dig", ctx.computed.stone_line)
        self.assertIn("high", ctx.computed.stone_line)

    def test_visible_stones_excludes_current_tile(self):
        world.state["stones"] = [
            _make_vein([5, 5]),
            _make_vein([6, 5], grade="medium", quantity=100, analyzed=True),
        ]
        world.state["agents"]["rover-mistral"]["revealed"] = [[5, 5], [6, 5]]
        ctx = observe_rover("rover-mistral")
        self.assertEqual(len(ctx.computed.visible_stones), 1)
        self.assertIn("basalt_vein", ctx.computed.visible_stones[0])

    def test_inventory_in_context(self):
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "high", "quantity": 200}
        ]
        ctx = observe_rover("rover-mistral")
        self.assertEqual(len(ctx.agent.inventory), 1)
        self.assertEqual(ctx.agent.inventory[0].type, "basalt_vein")
        self.assertEqual(ctx.agent.inventory[0].grade, "high")
        self.assertEqual(ctx.agent.inventory[0].quantity, 200)

    def test_mission_info(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.world.target_type, world.state["mission"]["target_type"])
        self.assertEqual(ctx.world.target_quantity, world.state["mission"]["target_quantity"])


class TestObserveStation(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [3, 4]
        world.state["agents"]["rover-mistral"]["battery"] = 0.5
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Scout", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0], [3, 4]]
        world.state["stones"] = [_make_vein([1, 1])]

    def test_returns_station_context_type(self):
        ctx = observe_station()
        self.assertIsInstance(ctx, StationContext)

    def test_grid_dimensions(self):
        ctx = observe_station()
        self.assertEqual(ctx.grid_w, GRID_W)
        self.assertEqual(ctx.grid_h, GRID_H)

    def test_rovers_list_excludes_station(self):
        ctx = observe_station()
        rover_ids = [r.id for r in ctx.rovers]
        self.assertNotIn("station", rover_ids)
        self.assertIn("rover-mistral", rover_ids)

    def test_rover_summary_fields(self):
        ctx = observe_station()
        rover = next(r for r in ctx.rovers if r.id == "rover-mistral")
        self.assertEqual(rover.position, [3, 4])
        self.assertAlmostEqual(rover.battery, 0.5)
        self.assertEqual(rover.mission.objective, "Scout")
        self.assertEqual(rover.visited_count, 2)

    def test_stones_list(self):
        ctx = observe_station()
        self.assertEqual(len(ctx.stones), 1)
        self.assertEqual(ctx.stones[0].position, [1, 1])
        self.assertEqual(ctx.stones[0].type, "unknown")


class TestDrone(unittest.TestCase):
    """Tests for drone agent: creation, scan action, movement, reveal radius."""

    def setUp(self):
        self.drone = world.state["agents"].get("drone-mistral")
        if self.drone:
            self.drone["position"] = [10, 10]
            self.drone["battery"] = 1.0
            self.drone["visited"] = [[10, 10]]
            self.drone["memory"] = []
        self._original_stones = list(world.state.get("stones", []))
        world.state.setdefault("drone_scans", []).clear()

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_drone_exists_in_world(self):
        self.assertIn("drone-mistral", world.state["agents"])
        self.assertEqual(world.state["agents"]["drone-mistral"]["type"], "drone")

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
        self.assertEqual(len(world.state["drone_scans"]), 1)

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
        world.state["stones"] = [_make_vein([10, 10], grade="high", quantity=200, analyzed=True)]
        result = execute_action("drone-mistral", "dig", {})
        self.assertFalse(result["ok"])

    def test_drone_tasks_scan_first(self):
        update_tasks("drone-mistral")
        tasks = self.drone["tasks"]
        self.assertTrue(any("Scan" in t or "scan" in t.lower() for t in tasks))

    def test_rover_tasks_use_drone_scans(self):
        """Rover should suggest navigating to drone-scanned hotspot."""
        world.state["stones"] = []
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0]]
        world.state["agents"]["rover-mistral"]["revealed"] = [
            [x, y] for x, y in sorted(_cells_in_radius(0, 0, ROVER_REVEAL_RADIUS))
        ]
        world.state["agents"]["rover-mistral"]["inventory"] = []
        # Add a high-concentration drone scan far from rover
        world.state["drone_scans"] = [
            {
                "position": [15, 15],
                "readings": {"15,15": 0.9, "14,15": 0.7},
                "peak": 0.9,
                "scanner": "drone-mistral",
            }
        ]
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertTrue(any("hotspot" in t for t in tasks))


class TestChunkSystem(unittest.TestCase):
    """Tests for infinite grid chunk-based procedural generation."""

    def test_chunk_generated_on_move(self):
        """Moving to a far tile generates the chunk."""
        world.state["agents"]["rover-mistral"]["position"] = [30, 30]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        result = move_agent("rover-mistral", 31, 30)
        self.assertTrue(result["ok"])
        # Chunk containing (31, 30) should exist
        from app.world import _chunk_key

        ck = _chunk_key(31, 30)
        self.assertIn(ck, world.state["chunks"])

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
        world.state["agents"]["rover-mistral"]["position"] = [-5, -5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        result = move_agent("rover-mistral", -6, -5)
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [-6, -5])

    def test_bounds_tracking(self):
        """World bounds update when agents move."""
        world.state["agents"]["rover-mistral"]["position"] = [50, 50]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        move_agent("rover-mistral", 51, 50)
        bounds = world.state["bounds"]
        self.assertGreaterEqual(bounds["max_x"], 51)

    def test_origin_chunk_has_vein(self):
        """Origin chunk should have at least one basalt_vein."""
        veins = [s for s in world.state["stones"] if s.get("_true_type") == "basalt_vein"]
        self.assertGreaterEqual(len(veins), 1)

    def test_get_concentration_lazy(self):
        """get_concentration generates chunk on demand."""
        from app.world import get_concentration, _chunk_key

        # Access a far-away cell
        val = get_concentration(100, 100)
        self.assertIsInstance(val, float)
        self.assertGreaterEqual(val, 0.0)
        ck = _chunk_key(100, 100)
        self.assertIn(ck, world.state["chunks"])

    def test_snapshot_includes_bounds(self):
        """Snapshot should include world bounds."""
        snap = get_snapshot()
        self.assertIn("bounds", snap)
        self.assertIn("min_x", snap["bounds"])
        self.assertIn("max_x", snap["bounds"])


class TestVeinGradeDistribution(unittest.TestCase):
    """Verify exponential rarity of vein grades via random sampling."""

    def test_grade_distribution_matches_weights(self):
        """Generate 10000 veins and verify grade distribution is roughly correct."""
        rng = random.Random(12345)
        counts = {g: 0 for g in VEIN_GRADES}
        n = 10000
        for _ in range(n):
            grade = rng.choices(VEIN_GRADES, weights=VEIN_WEIGHTS, k=1)[0]
            counts[grade] += 1
        total_weight = sum(VEIN_WEIGHTS)
        for i, grade in enumerate(VEIN_GRADES):
            expected_pct = VEIN_WEIGHTS[i] / total_weight
            actual_pct = counts[grade] / n
            # Allow generous tolerance (5% absolute) for statistical sampling
            self.assertAlmostEqual(
                actual_pct,
                expected_pct,
                delta=0.05,
                msg=f"Grade '{grade}': expected ~{expected_pct:.1%}, got {actual_pct:.1%}",
            )

    def test_quantity_ranges_per_grade(self):
        """Verify that random quantities stay within defined ranges."""
        rng = random.Random(99999)
        for grade, (lo, hi) in VEIN_QUANTITY_RANGES.items():
            for _ in range(100):
                qty = rng.randint(lo, hi)
                self.assertGreaterEqual(qty, lo)
                self.assertLessEqual(qty, hi)

    def test_low_is_most_common(self):
        """Low grade should have the highest weight."""
        self.assertEqual(VEIN_GRADES[0], "low")
        self.assertEqual(max(VEIN_WEIGHTS), VEIN_WEIGHTS[0])

    def test_pristine_is_rarest(self):
        """Pristine grade should have the lowest weight."""
        self.assertEqual(VEIN_GRADES[-1], "pristine")
        self.assertEqual(min(VEIN_WEIGHTS), VEIN_WEIGHTS[-1])

    def test_weights_decrease_monotonically(self):
        """Weights should decrease from low to pristine."""
        for i in range(len(VEIN_WEIGHTS) - 1):
            self.assertGreater(VEIN_WEIGHTS[i], VEIN_WEIGHTS[i + 1])


class TestAbortMission(unittest.TestCase):
    def setUp(self):
        self._original_status = world.state["mission"]["status"]

    def tearDown(self):
        world.state["mission"]["status"] = self._original_status

    def test_abort_sets_status(self):
        world.state["mission"]["status"] = "running"
        result = abort_mission("test reason")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "aborted")
        self.assertEqual(result["reason"], "test reason")
        self.assertEqual(world.state["mission"]["status"], "aborted")

    def test_abort_noop_when_success(self):
        world.state["mission"]["status"] = "success"
        result = abort_mission("too late")
        self.assertIsNone(result)

    def test_abort_noop_when_failed(self):
        world.state["mission"]["status"] = "failed"
        result = abort_mission("too late")
        self.assertIsNone(result)

    def test_abort_noop_when_already_aborted(self):
        world.state["mission"]["status"] = "aborted"
        result = abort_mission("again")
        self.assertIsNone(result)

    def test_abort_default_reason(self):
        world.state["mission"]["status"] = "running"
        result = abort_mission()
        self.assertIn("Manual abort", result["reason"])

    def test_abort_updates_agent_objectives(self):
        world.state["mission"]["status"] = "running"
        world.state["agents"]["rover-mistral"]["mission"]["objective"] = "Collect veins"
        abort_mission("test")
        self.assertIn("ABORTED", world.state["agents"]["rover-mistral"]["mission"]["objective"])

    def test_abort_tasks_override(self):
        """During abort, update_tasks should set 'return to station' task."""
        world.state["mission"]["status"] = "aborted"
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertIn("MISSION ABORTED", tasks[0])
        self.assertIn("return to station", tasks[0])

    def test_abort_tasks_at_station(self):
        """During abort, agent at station gets standing-by task."""
        world.state["mission"]["status"] = "aborted"
        station_pos = world.state["agents"]["station"]["position"]
        world.state["agents"]["rover-mistral"]["position"] = list(station_pos)
        update_tasks("rover-mistral")
        tasks = world.state["agents"]["rover-mistral"]["tasks"]
        self.assertIn("standing by", tasks[0])

    def test_all_agents_at_station_true(self):
        station_pos = world.state["agents"]["station"]["position"]
        for aid, agent in world.state["agents"].items():
            if agent.get("type") in ("rover", "drone"):
                agent["position"] = list(station_pos)
        self.assertTrue(all_agents_at_station())

    def test_all_agents_at_station_false(self):
        world.state["agents"]["rover-mistral"]["position"] = [99, 99]
        self.assertFalse(all_agents_at_station())


class TestChargeAgent(unittest.TestCase):
    """Test charge_agent for non-rover agents (drone)."""

    def setUp(self):
        self.drone = world.state["agents"].get("drone-mistral")
        if self.drone:
            self.drone["position"] = [0, 0]
            self.drone["battery"] = 0.5
            self.drone["memory"] = []
        world.state["agents"]["station"]["position"] = [0, 0]

    def test_charge_drone(self):
        result = charge_agent("drone-mistral")
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_before"], 0.5)
        self.assertAlmostEqual(result["battery_after"], 0.5 + CHARGE_RATE)


class TestStoneProximityConcentration(unittest.TestCase):
    """Test proximity-based concentration replaces noise-based."""

    def setUp(self):
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_concentration_at_stone(self):
        from app.world import _stone_proximity_concentration

        world.state["stones"] = [_make_vein([5, 5])]
        self.assertEqual(_stone_proximity_concentration(5, 5), 1.0)

    def test_concentration_falls_off(self):
        from app.world import _stone_proximity_concentration

        world.state["stones"] = [_make_vein([5, 5])]
        val_near = _stone_proximity_concentration(6, 5)
        val_far = _stone_proximity_concentration(10, 5)
        self.assertGreater(val_near, val_far)

    def test_concentration_zero_far_away(self):
        from app.world import _stone_proximity_concentration

        world.state["stones"] = [_make_vein([5, 5])]
        val = _stone_proximity_concentration(50, 50)
        self.assertEqual(val, 0.0)


class TestNotifyBase(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "rich", "quantity": 400},
        ]
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = []

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_notify_base_success(self):
        result = execute_action("rover-mistral", "notify_base", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["position"], [5, 5])
        self.assertIn("rich", result["message"])
        self.assertEqual(len(result["inventory_summary"]), 1)
        self.assertEqual(result["inventory_summary"][0]["grade"], "rich")
        self.assertEqual(result["inventory_summary"][0]["quantity"], 400)
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_NOTIFY
        )

    def test_notify_base_empty_inventory(self):
        world.state["agents"]["rover-mistral"]["inventory"] = []
        result = execute_action("rover-mistral", "notify_base", {})
        self.assertFalse(result["ok"])
        self.assertIn("empty", result["error"])

    def test_notify_base_low_battery(self):
        world.state["agents"]["rover-mistral"]["battery"] = 0.0
        result = execute_action("rover-mistral", "notify_base", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_notify_base_drone_rejected(self):
        result = execute_action("drone-mistral", "notify_base", {})
        self.assertFalse(result["ok"])
        self.assertIn("Drones cannot", result["error"])


class TestInTransitQuantity(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "high", "quantity": 200},
        ]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["mission"]["status"] = "running"
        world.state["mission"]["target_type"] = "basalt_vein"
        world.state["mission"]["target_quantity"] = 500
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = []

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_in_transit_quantity_tracked(self):
        check_mission_status()
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 200)

    def test_in_transit_zero_when_at_station(self):
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        check_mission_status()
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 0)


class TestWorldSetters(unittest.TestCase):
    def test_set_agent_model(self):
        set_agent_model("rover-mistral", "test-model")
        self.assertEqual(world.state["agents"]["rover-mistral"]["model"], "test-model")

    def test_set_agent_last_context(self):
        set_agent_last_context("rover-mistral", "some prompt")
        self.assertEqual(world.state["agents"]["rover-mistral"]["last_context"], "some prompt")

    def test_set_pending_commands_set_and_clear(self):
        set_pending_commands("rover-mistral", [{"name": "recall"}])
        self.assertEqual(
            world.state["agents"]["rover-mistral"]["pending_commands"], [{"name": "recall"}]
        )
        set_pending_commands("rover-mistral", None)
        self.assertNotIn("pending_commands", world.state["agents"]["rover-mistral"])


class TestWorldClass(unittest.TestCase):
    def test_singleton_wraps_module_world(self):
        """Module-level `world` singleton is the canonical instance."""
        from app.world import world as w

        self.assertIs(w.state, world.state)

    def test_get_agent(self):
        agent = world.get_agent("rover-mistral")
        self.assertEqual(agent["type"], "rover")

    def test_get_agents_returns_all(self):
        agents = world.get_agents()
        self.assertIn("rover-mistral", agents)
        self.assertIn("station", agents)

    def test_get_mission(self):
        mission = world.get_mission()
        self.assertIn("status", mission)

    def test_setters_delegate_to_state(self):
        world.set_agent_model("rover-mistral", "test-via-class")
        self.assertEqual(world.state["agents"]["rover-mistral"]["model"], "test-via-class")

        world.set_agent_last_context("rover-mistral", "ctx-via-class")
        self.assertEqual(world.state["agents"]["rover-mistral"]["last_context"], "ctx-via-class")

        world.set_pending_commands("rover-mistral", [{"name": "test"}])
        self.assertEqual(
            world.state["agents"]["rover-mistral"]["pending_commands"], [{"name": "test"}]
        )
        world.set_pending_commands("rover-mistral", None)
        self.assertNotIn("pending_commands", world.state["agents"]["rover-mistral"])

    def test_get_tick(self):
        self.assertEqual(world.get_tick(), world.state["tick"])

    def test_fresh_instance_independent(self):
        """A World() with no args gets its own state, independent of the singleton."""
        from app.world import World

        w2 = World()
        w2.set_agent_model("rover-mistral", "independent-model")
        self.assertNotEqual(
            world.state["agents"]["rover-mistral"].get("model"),
            "independent-model",
        )
