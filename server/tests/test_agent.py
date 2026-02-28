import unittest

from app.world import WORLD, GRID_W, GRID_H
from app.agent import MockRoverReasoner
from app.models import AgentMission, InventoryItem, PendingCommand, StoneInfo
from app.models import RoverAgentState, RoverWorldView, RoverComputed, RoverContext


def _make_rover_context(agent_id="rover-mock", **overrides):
    """Build a typed RoverContext for testing, reading from WORLD."""
    agent = WORLD["agents"][agent_id]
    mission_data = WORLD.get("mission", {})

    agent_state = RoverAgentState(
        position=list(agent["position"]),
        battery=agent["battery"],
        mission=AgentMission(**agent["mission"]),
        inventory=[InventoryItem(**i) for i in agent.get("inventory", [])],
        memory=list(agent.get("memory", [])),
        tasks=list(agent.get("tasks", [])),
        visited=list(agent.get("visited", [])),
        visited_count=len(agent.get("visited", [])),
        ground_readings=dict(agent.get("ground_readings", {})),
    )
    world_view = RoverWorldView(
        grid_w=GRID_W,
        grid_h=GRID_H,
        station_position=[0, 0],
        target_type=mission_data.get("target_type", "core"),
        target_count=mission_data.get("target_count", 2),
        collected_count=mission_data.get("collected_count", 0),
    )
    computed = RoverComputed()

    # Apply overrides to the appropriate section
    agent_overrides = {}
    world_overrides = {}
    computed_overrides = {}
    for key, val in overrides.items():
        if key in RoverAgentState.model_fields:
            agent_overrides[key] = val
        elif key in RoverWorldView.model_fields:
            world_overrides[key] = val
        elif key in RoverComputed.model_fields:
            computed_overrides[key] = val

    if agent_overrides:
        agent_state = agent_state.model_copy(update=agent_overrides)
    if world_overrides:
        world_view = world_view.model_copy(update=world_overrides)
    if computed_overrides:
        computed = computed.model_copy(update=computed_overrides)

    return RoverContext(agent=agent_state, world=world_view, computed=computed)


class TestMockRoverAgent(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]

    def test_run_turn_returns_dict(self):
        agent = MockRoverReasoner()
        ctx = _make_rover_context()
        turn = agent.run_turn(ctx)
        self.assertIsInstance(turn, dict)
        self.assertIn("thinking", turn)
        self.assertIn("action", turn)

    def test_run_turn_has_thinking(self):
        agent = MockRoverReasoner()
        ctx = _make_rover_context()
        turn = agent.run_turn(ctx)
        self.assertIsInstance(turn["thinking"], str)
        self.assertTrue(len(turn["thinking"]) > 0)

    def test_run_turn_action_shape(self):
        agent = MockRoverReasoner()
        ctx = _make_rover_context()
        turn = agent.run_turn(ctx)
        action = turn["action"]
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "move")
        self.assertIn("direction", action["params"])
        self.assertIn(action["params"]["direction"], ["north", "south", "east", "west"])

    def test_run_turn_does_not_mutate_world(self):
        agent = MockRoverReasoner()
        pos_before = list(WORLD["agents"]["rover-mock"]["position"])
        ctx = _make_rover_context()
        agent.run_turn(ctx)
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], pos_before)

    def test_run_turn_at_corner(self):
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        agent = MockRoverReasoner()
        ctx = _make_rover_context()
        turn = agent.run_turn(ctx)
        self.assertIn(turn["action"]["params"]["direction"], ["north", "east"])

    def test_run_turn_at_bottom_right(self):
        WORLD["agents"]["rover-mock"]["position"] = [GRID_W - 1, GRID_H - 1]
        WORLD["agents"]["rover-mock"]["visited"] = [[GRID_W - 1, GRID_H - 1]]
        agent = MockRoverReasoner()
        ctx = _make_rover_context()
        turn = agent.run_turn(ctx)
        self.assertIn(turn["action"]["params"]["direction"], ["south", "west"])

    def test_mock_prefers_unvisited(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["visited"] = [
            [10, 10],
            [11, 10],
            [10, 9],
            [9, 10],
        ]
        agent = MockRoverReasoner()
        ctx = _make_rover_context()
        turn = agent.run_turn(ctx)
        self.assertEqual(turn["action"]["params"]["direction"], "north")

    def test_mock_analyzes_unknown_stone(self):
        agent = MockRoverReasoner()
        stone = StoneInfo(position=[10, 10], type="unknown", analyzed=False, extracted=False)
        ctx = _make_rover_context(stone_here=stone)
        turn = agent.run_turn(ctx)
        self.assertEqual(turn["action"]["name"], "analyze")

    def test_mock_digs_analyzed_stone(self):
        agent = MockRoverReasoner()
        stone = StoneInfo(position=[10, 10], type="core", analyzed=True, extracted=False)
        ctx = _make_rover_context(stone_here=stone)
        turn = agent.run_turn(ctx)
        self.assertEqual(turn["action"]["name"], "dig")

    def test_mock_picks_up_extracted_stone(self):
        agent = MockRoverReasoner()
        stone = StoneInfo(position=[10, 10], type="core", analyzed=True, extracted=True)
        ctx = _make_rover_context(stone_here=stone)
        turn = agent.run_turn(ctx)
        self.assertEqual(turn["action"]["name"], "pickup")

    def test_mock_returns_to_station_with_target(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        agent = MockRoverReasoner()
        ctx = _make_rover_context(
            inventory=[InventoryItem(type="core")],
            station_position=[0, 0],
        )
        turn = agent.run_turn(ctx)
        self.assertEqual(turn["action"]["name"], "move")
        # Should head toward station (west or south)
        self.assertIn(turn["action"]["params"]["direction"], ["west", "south"])

    def test_mock_recall_heads_to_station(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        agent = MockRoverReasoner()
        recall = PendingCommand(name="recall", payload={"reason": "Emergency"})
        ctx = _make_rover_context(pending_commands=[recall])
        turn = agent.run_turn(ctx)
        self.assertEqual(turn["action"]["name"], "move")
        # Should head toward station at (0,0) — west or south
        self.assertIn(turn["action"]["params"]["direction"], ["west", "south"])
        self.assertIn("RECALL", turn["thinking"])

    def test_mock_recall_overrides_stone(self):
        """Recall should take priority over stone interaction."""
        agent = MockRoverReasoner()
        stone = StoneInfo(position=[10, 10], type="unknown", analyzed=False)
        recall = PendingCommand(name="recall", payload={"reason": "Storm"})
        ctx = _make_rover_context(stone_here=stone, pending_commands=[recall])
        turn = agent.run_turn(ctx)
        # Should move, not analyze
        self.assertEqual(turn["action"]["name"], "move")
        self.assertIn("RECALL", turn["thinking"])

    def test_mock_recall_at_station(self):
        """If already at station when recall received, still returns valid action."""
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        agent = MockRoverReasoner()
        recall = PendingCommand(name="recall", payload={"reason": "Test"})
        ctx = _make_rover_context(
            pending_commands=[recall],
            station_position=[0, 0],
        )
        turn = agent.run_turn(ctx)
        self.assertIn("already at station", turn["thinking"])
