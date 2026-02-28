import unittest

from app.models import AgentMission, InventoryItem, StoneInfo
from app.models import RoverAgentState, RoverWorldView, RoverComputed, RoverContext
from app.models import RoverSummary, StationContext


class TestStoneInfo(unittest.TestCase):
    def test_defaults(self):
        s = StoneInfo(position=[5, 5], type="core")
        self.assertFalse(s.extracted)
        self.assertFalse(s.analyzed)

    def test_full(self):
        s = StoneInfo(position=[1, 2], type="basalt", extracted=True, analyzed=True)
        self.assertTrue(s.extracted)
        self.assertTrue(s.analyzed)
        self.assertEqual(s.type, "basalt")


class TestRoverContext(unittest.TestCase):
    def _make(self, **overrides):
        agent = RoverAgentState(
            position=[10, 10],
            battery=1.0,
            mission=AgentMission(objective="Explore"),
        )
        world = RoverWorldView(
            grid_w=20,
            grid_h=20,
            station_position=[0, 0],
        )
        computed = RoverComputed()
        kwargs = {"agent": agent, "world": world, "computed": computed}
        kwargs.update(overrides)
        return RoverContext(**kwargs)

    def test_construction(self):
        ctx = self._make()
        self.assertEqual(ctx.agent.position, [10, 10])
        self.assertEqual(ctx.agent.battery, 1.0)
        self.assertEqual(ctx.world.grid_w, 20)
        self.assertIsNone(ctx.computed.stone_here)

    def test_stone_here_typed(self):
        stone = StoneInfo(position=[10, 10], type="core", analyzed=True)
        ctx = self._make(computed=RoverComputed(stone_here=stone))
        self.assertEqual(ctx.computed.stone_here.type, "core")
        self.assertTrue(ctx.computed.stone_here.analyzed)

    def test_inventory_typed(self):
        agent = RoverAgentState(
            position=[0, 0],
            battery=0.5,
            mission=AgentMission(objective="Collect"),
            inventory=[InventoryItem(type="core")],
        )
        ctx = self._make(agent=agent)
        self.assertEqual(ctx.agent.inventory[0].type, "core")

    def test_model_dump_roundtrip(self):
        ctx = self._make()
        data = ctx.model_dump()
        ctx2 = RoverContext(**data)
        self.assertEqual(ctx2.agent.position, ctx.agent.position)


class TestStationContext(unittest.TestCase):
    def test_construction(self):
        ctx = StationContext(
            grid_w=20,
            grid_h=20,
            rovers=[
                RoverSummary(
                    id="rover-mock",
                    position=[0, 0],
                    battery=1.0,
                    mission=AgentMission(objective="Explore"),
                ),
            ],
            stones=[StoneInfo(position=[5, 5], type="unknown")],
        )
        self.assertEqual(len(ctx.rovers), 1)
        self.assertEqual(ctx.rovers[0].id, "rover-mock")
        self.assertEqual(ctx.rovers[0].mission.objective, "Explore")
        self.assertEqual(len(ctx.stones), 1)

    def test_empty_rovers_and_stones(self):
        ctx = StationContext(grid_w=10, grid_h=10, rovers=[], stones=[])
        self.assertEqual(len(ctx.rovers), 0)
        self.assertEqual(len(ctx.stones), 0)
