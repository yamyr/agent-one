"""Tests for the dynamic world events engine."""

import unittest
from app.events import EventEngine, WorldEvent


class TestWorldEvent(unittest.TestCase):
    def test_event_creation(self):
        ev = WorldEvent(name="dust_storm", description="A dust storm", tick=10, duration=5)
        self.assertEqual(ev.name, "dust_storm")
        self.assertTrue(ev.active)
        self.assertEqual(ev.effects, {})

    def test_event_with_effects(self):
        ev = WorldEvent(name="solar_flare", description="Solar flare", tick=5, duration=3,
                        effects={"solar_boost": 1.5})
        self.assertEqual(ev.effects["solar_boost"], 1.5)


class TestEventEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EventEngine()
        self.world = {"tick": 0, "agents": {"rover-mistral": {"position": [10, 10], "battery": 100}}, "stones": []}

    def test_no_events_before_threshold(self):
        new = self.engine.tick(5, self.world)
        self.assertEqual(len(new), 0)

    def test_event_generated_at_threshold(self):
        new = self.engine.tick(15, self.world)
        self.assertEqual(len(new), 1)
        self.assertIn(new[0].name, ["dust_storm", "solar_flare", "seismic_reading", "comm_interference"])

    def test_event_expires(self):
        ev = WorldEvent(name="test", description="test", tick=10, duration=3)
        self.engine.active_events.append(ev)
        self.engine.tick(13, self.world)
        self.assertEqual(len(self.engine.active_events), 0)
        self.assertEqual(len(self.engine.event_history), 1)

    def test_instant_event_not_expired_by_duration(self):
        ev = WorldEvent(name="seismic", description="test", tick=10, duration=0)
        self.engine.active_events.append(ev)
        self.engine.tick(12, self.world)
        self.assertEqual(len(self.engine.active_events), 1)

    def test_reset(self):
        self.engine.active_events.append(WorldEvent(name="test", description="test", tick=1, duration=5))
        self.engine.event_history.append(WorldEvent(name="old", description="old", tick=0, duration=1, active=False))
        self.engine.reset()
        self.assertEqual(len(self.engine.active_events), 0)
        self.assertEqual(len(self.engine.event_history), 0)
        self.assertEqual(self.engine.next_event_tick, 15)


class TestMergedEffects(unittest.TestCase):
    def setUp(self):
        self.engine = EventEngine()

    def test_single_effect(self):
        self.engine.active_events.append(
            WorldEvent(name="storm", description="storm", tick=1, duration=5, effects={"move_cost_modifier": 1.3}))
        self.assertAlmostEqual(self.engine.get_active_effects()["move_cost_modifier"], 1.3)

    def test_stacked_effects(self):
        self.engine.active_events.append(
            WorldEvent(name="storm", description="storm", tick=1, duration=5, effects={"move_cost_modifier": 1.3}))
        self.engine.active_events.append(
            WorldEvent(name="flare", description="flare", tick=2, duration=3, effects={"move_cost_modifier": 1.2}))
        self.assertAlmostEqual(self.engine.get_active_effects()["move_cost_modifier"], 1.3 * 1.2)

    def test_no_effects(self):
        self.assertEqual(self.engine.get_active_effects(), {})


class TestActiveDescriptions(unittest.TestCase):
    def setUp(self):
        self.engine = EventEngine()

    def test_descriptions(self):
        self.engine.active_events.append(WorldEvent(name="storm", description="Big storm!", tick=1, duration=5))
        self.engine.active_events.append(WorldEvent(name="flare", description="Solar flare!", tick=2, duration=3))
        descs = self.engine.get_active_descriptions()
        self.assertEqual(len(descs), 2)
        self.assertIn("Big storm!", descs)

    def test_empty(self):
        self.assertEqual(self.engine.get_active_descriptions(), [])


class TestActiveEventsData(unittest.TestCase):
    def setUp(self):
        self.engine = EventEngine()

    def test_serializable_data(self):
        self.engine.active_events.append(
            WorldEvent(name="storm", description="test", tick=5, duration=3, effects={"mod": 1.5}))
        data = self.engine.get_active_events_data()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "storm")


class TestModifiedCosts(unittest.TestCase):
    def test_no_events_no_change(self):
        from app.world import _get_modified_cost
        from app.events import event_engine
        event_engine.reset()
        self.assertAlmostEqual(_get_modified_cost(10.0, "move_cost_modifier"), 10.0)

    def test_with_modifier(self):
        from app.world import _get_modified_cost
        from app.events import event_engine
        event_engine.reset()
        event_engine.active_events.append(
            WorldEvent(name="flare", description="flare", tick=1, duration=5, effects={"move_cost_modifier": 2.0}))
        self.assertAlmostEqual(_get_modified_cost(10.0, "move_cost_modifier"), 20.0)
        event_engine.reset()


class TestApplySeismicEvent(unittest.TestCase):
    def test_places_vein(self):
        from app.world import apply_seismic_event, WORLD
        WORLD.setdefault("stones", [])
        initial_count = len(WORLD["stones"])
        apply_seismic_event({"reveal_vein": [20, 20], "vein_grade": "high"})
        self.assertEqual(len(WORLD["stones"]), initial_count + 1)
        new_stone = WORLD["stones"][-1]
        self.assertEqual(new_stone["position"], [20, 20])
        self.assertEqual(new_stone["_true_grade"], "high")
        WORLD["stones"] = [s for s in WORLD["stones"] if s["position"] != [20, 20]]


if __name__ == "__main__":
    unittest.main()
