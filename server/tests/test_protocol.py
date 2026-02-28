import unittest

from app.protocol import Message, make_message
from app.world import world


class TestMessage(unittest.TestCase):
    def test_message_has_all_fields(self):
        msg = Message(
            source="rover-mock",
            type="action",
            name="move",
            payload={"direction": "north"},
        )
        self.assertIsInstance(msg.id, str)
        self.assertGreater(len(msg.id), 0)
        self.assertIsInstance(msg.ts, float)
        self.assertIsInstance(msg.tick, int)
        self.assertEqual(msg.source, "rover-mock")
        self.assertEqual(msg.type, "action")
        self.assertEqual(msg.name, "move")
        self.assertEqual(msg.payload, {"direction": "north"})
        self.assertIsNone(msg.correlation_id)

    def test_message_with_correlation_id(self):
        msg = Message(
            source="station",
            type="command",
            name="assign_mission",
            payload={"agent_id": "rover-mock"},
            correlation_id="abc-123",
        )
        self.assertEqual(msg.correlation_id, "abc-123")

    def test_to_dict(self):
        msg = Message(
            source="world",
            type="event",
            name="state",
            payload={"tick": 1},
        )
        d = msg.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["source"], "world")
        self.assertEqual(d["type"], "event")
        self.assertEqual(d["name"], "state")
        self.assertEqual(d["payload"], {"tick": 1})
        self.assertIn("id", d)
        self.assertIn("ts", d)
        self.assertIn("tick", d)
        self.assertIn("correlation_id", d)

    def test_unique_ids(self):
        msg1 = make_message("rover-mock", "action", "move", {})
        msg2 = make_message("rover-mock", "action", "move", {})
        self.assertNotEqual(msg1.id, msg2.id)


class TestMakeMessage(unittest.TestCase):
    def test_make_message_basic(self):
        msg = make_message("rover-mock", "action", "move", {"direction": "north"})
        self.assertEqual(msg.source, "rover-mock")
        self.assertEqual(msg.type, "action")
        self.assertEqual(msg.name, "move")
        self.assertEqual(msg.payload, {"direction": "north"})
        self.assertIsNone(msg.correlation_id)

    def test_make_message_with_correlation(self):
        trigger = make_message("rover-mock", "event", "check", {"stone": "core"})
        response = make_message(
            "station",
            "command",
            "assign_mission",
            {"agent_id": "rover-mock"},
            correlation_id=trigger.id,
        )
        self.assertEqual(response.correlation_id, trigger.id)

    def test_make_message_uses_current_tick(self):
        original_tick = world.get_tick()
        msg = make_message("world", "event", "state", {})
        self.assertEqual(msg.tick, original_tick)

    def test_to_dict_serializable(self):
        """Ensure to_dict produces JSON-serializable output."""
        import json

        msg = make_message("rover-mock", "action", "dig", {"x": 1, "y": 2})
        d = msg.to_dict()
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)
