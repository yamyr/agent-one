import json
import unittest

from pydantic import ValidationError

from app.protocol import (
    ActionMessage,
    BaseMessage,
    CommandMessage,
    EventMessage,
    Message,
    MessageType,
    StreamMessage,
    ToolMessage,
    make_message,
    parse_message,
)
from app.world import world


# ── Existing tests (updated to use typed constructors) ──────────────────────


class TestMessage(unittest.TestCase):
    """Original tests updated to use typed constructors."""

    def test_message_has_all_fields(self):
        msg = ActionMessage(
            source="rover-mock",
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
        msg = CommandMessage(
            source="station",
            name="assign_mission",
            payload={"agent_id": "rover-mock"},
            correlation_id="abc-123",
        )
        self.assertEqual(msg.correlation_id, "abc-123")

    def test_to_dict(self):
        msg = EventMessage(
            source="world",
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
    """Original tests — make_message still works the same way."""

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
        msg = make_message("rover-mock", "action", "dig", {"x": 1, "y": 2})
        d = msg.to_dict()
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)


# ── US1: Type-Safe Message Construction ─────────────────────────────────────


class TestTypedConstructors(unittest.TestCase):
    """US1: Each typed constructor sets the correct literal type."""

    def test_action_message_type(self):
        msg = ActionMessage(source="rover", name="move", payload={})
        self.assertEqual(msg.type, "action")

    def test_event_message_type(self):
        msg = EventMessage(source="world", name="state", payload={})
        self.assertEqual(msg.type, "event")

    def test_command_message_type(self):
        msg = CommandMessage(source="station", name="assign", payload={})
        self.assertEqual(msg.type, "command")

    def test_tool_message_type(self):
        msg = ToolMessage(source="rover", name="drill", payload={})
        self.assertEqual(msg.type, "tool")

    def test_stream_message_type(self):
        msg = StreamMessage(source="drone", name="scan", payload={})
        self.assertEqual(msg.type, "stream")

    def test_all_five_types_instantiate(self):
        """All five message types can be instantiated with required fields."""
        classes = [ActionMessage, EventMessage, CommandMessage, ToolMessage, StreamMessage]
        expected_types = ["action", "event", "command", "tool", "stream"]
        for cls, expected in zip(classes, expected_types):
            msg = cls(source="test", name="test", payload={"k": "v"})
            self.assertEqual(msg.type, expected, f"{cls.__name__} type mismatch")

    def test_auto_generated_id(self):
        msg = ActionMessage(source="rover", name="move", payload={})
        self.assertIsInstance(msg.id, str)
        self.assertGreater(len(msg.id), 0)

    def test_auto_generated_ts(self):
        msg = ActionMessage(source="rover", name="move", payload={})
        self.assertIsInstance(msg.ts, float)
        self.assertGreater(msg.ts, 0)

    def test_auto_generated_tick(self):
        msg = ActionMessage(source="rover", name="move", payload={})
        self.assertIsInstance(msg.tick, int)

    def test_correlation_id_defaults_to_none(self):
        msg = ActionMessage(source="rover", name="move", payload={})
        self.assertIsNone(msg.correlation_id)

    def test_correlation_id_can_be_set(self):
        msg = ActionMessage(source="rover", name="move", payload={}, correlation_id="corr-123")
        self.assertEqual(msg.correlation_id, "corr-123")

    def test_invalid_type_override_raises_error(self):
        """Attempting to set type to an invalid value on a typed subclass raises error."""
        with self.assertRaises(ValidationError):
            ActionMessage(source="rover", type="event", name="move", payload={})

    def test_message_type_enum_values(self):
        """MessageType enum has exactly five values."""
        self.assertEqual(len(MessageType), 5)
        self.assertEqual(MessageType.ACTION, "action")
        self.assertEqual(MessageType.EVENT, "event")
        self.assertEqual(MessageType.COMMAND, "command")
        self.assertEqual(MessageType.TOOL, "tool")
        self.assertEqual(MessageType.STREAM, "stream")


# ── US2: Backward-Compatible Serialization ──────────────────────────────────


class TestSerialization(unittest.TestCase):
    """US2: to_dict() output is structurally identical to old asdict()."""

    EXPECTED_KEYS = {"id", "ts", "tick", "source", "type", "name", "payload", "correlation_id"}

    def test_to_dict_has_exact_keys(self):
        msg = ActionMessage(source="rover", name="move", payload={"direction": "north"})
        d = msg.to_dict()
        self.assertEqual(set(d.keys()), self.EXPECTED_KEYS)

    def test_to_dict_all_types_same_keys(self):
        """Every typed subclass produces the same key set."""
        classes = [ActionMessage, EventMessage, CommandMessage, ToolMessage, StreamMessage]
        for cls in classes:
            msg = cls(source="test", name="test", payload={})
            d = msg.to_dict()
            self.assertEqual(set(d.keys()), self.EXPECTED_KEYS, f"{cls.__name__} key mismatch")

    def test_to_dict_json_serializable(self):
        msg = ActionMessage(source="rover", name="move", payload={"x": 1})
        d = msg.to_dict()
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["source"], "rover")

    def test_correlation_id_none_present_in_output(self):
        msg = EventMessage(source="world", name="state", payload={})
        d = msg.to_dict()
        self.assertIn("correlation_id", d)
        self.assertIsNone(d["correlation_id"])

    def test_empty_payload_serializes(self):
        msg = ActionMessage(source="rover", name="noop", payload={})
        d = msg.to_dict()
        self.assertEqual(d["payload"], {})

    def test_deeply_nested_payload_serializes(self):
        deep_payload = {"level1": {"level2": {"level3": [1, 2, {"level4": True}]}}}
        msg = EventMessage(source="world", name="complex", payload=deep_payload)
        d = msg.to_dict()
        self.assertEqual(d["payload"], deep_payload)

    def test_to_dict_values_match_fields(self):
        msg = CommandMessage(
            source="station",
            name="assign",
            payload={"agent_id": "r1"},
            correlation_id="c-1",
        )
        d = msg.to_dict()
        self.assertEqual(d["source"], msg.source)
        self.assertEqual(d["type"], msg.type)
        self.assertEqual(d["name"], msg.name)
        self.assertEqual(d["payload"], msg.payload)
        self.assertEqual(d["id"], msg.id)
        self.assertEqual(d["ts"], msg.ts)
        self.assertEqual(d["tick"], msg.tick)
        self.assertEqual(d["correlation_id"], msg.correlation_id)


# ── US1 (make_message factory) ──────────────────────────────────────────────


class TestMakeMessageFactory(unittest.TestCase):
    """US1: make_message() returns the correct typed subclass."""

    def test_returns_action_message(self):
        msg = make_message("rover", "action", "move", {})
        self.assertIsInstance(msg, ActionMessage)

    def test_returns_event_message(self):
        msg = make_message("world", "event", "state", {})
        self.assertIsInstance(msg, EventMessage)

    def test_returns_command_message(self):
        msg = make_message("station", "command", "assign", {})
        self.assertIsInstance(msg, CommandMessage)

    def test_returns_tool_message(self):
        msg = make_message("rover", "tool", "drill", {})
        self.assertIsInstance(msg, ToolMessage)

    def test_returns_stream_message(self):
        msg = make_message("drone", "stream", "scan", {})
        self.assertIsInstance(msg, StreamMessage)

    def test_preserves_all_arguments(self):
        msg = make_message("rover-1", "action", "dig", {"x": 5}, correlation_id="c-99")
        self.assertEqual(msg.source, "rover-1")
        self.assertEqual(msg.type, "action")
        self.assertEqual(msg.name, "dig")
        self.assertEqual(msg.payload, {"x": 5})
        self.assertEqual(msg.correlation_id, "c-99")

    def test_unique_ids_per_call(self):
        msg1 = make_message("rover", "action", "move", {})
        msg2 = make_message("rover", "action", "move", {})
        self.assertNotEqual(msg1.id, msg2.id)


# ── US3: Message Deserialization with Discriminator ─────────────────────────


class TestParseMessage(unittest.TestCase):
    """US3: parse_message() correctly resolves types from raw dicts."""

    def _make_raw(self, msg_type: str, **overrides) -> dict:
        base = {
            "source": "test",
            "type": msg_type,
            "name": "test",
            "payload": {},
            "id": "test-id",
            "ts": 1.0,
            "tick": 0,
            "correlation_id": None,
        }
        base.update(overrides)
        return base

    def test_parse_action(self):
        msg = parse_message(self._make_raw("action"))
        self.assertIsInstance(msg, ActionMessage)
        self.assertEqual(msg.type, "action")

    def test_parse_event(self):
        msg = parse_message(self._make_raw("event"))
        self.assertIsInstance(msg, EventMessage)
        self.assertEqual(msg.type, "event")

    def test_parse_command(self):
        msg = parse_message(self._make_raw("command"))
        self.assertIsInstance(msg, CommandMessage)
        self.assertEqual(msg.type, "command")

    def test_parse_tool(self):
        msg = parse_message(self._make_raw("tool"))
        self.assertIsInstance(msg, ToolMessage)
        self.assertEqual(msg.type, "tool")

    def test_parse_stream(self):
        msg = parse_message(self._make_raw("stream"))
        self.assertIsInstance(msg, StreamMessage)
        self.assertEqual(msg.type, "stream")

    def test_invalid_type_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            parse_message(self._make_raw("unknown"))

    def test_missing_required_fields_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            parse_message({"type": "action"})  # missing source, name, payload

    def test_extra_fields_ignored(self):
        raw = self._make_raw("action", extra_field="should_be_ignored")
        msg = parse_message(raw)
        self.assertIsInstance(msg, ActionMessage)
        self.assertFalse(hasattr(msg, "extra_field"))

    def test_round_trip(self):
        """create message -> to_dict() -> parse_message() produces equivalent instance."""
        original = ActionMessage(
            source="rover",
            name="move",
            payload={"direction": "north"},
            correlation_id="c-1",
        )
        d = original.to_dict()
        parsed = parse_message(d)
        self.assertIsInstance(parsed, ActionMessage)
        self.assertEqual(parsed.source, original.source)
        self.assertEqual(parsed.type, original.type)
        self.assertEqual(parsed.name, original.name)
        self.assertEqual(parsed.payload, original.payload)
        self.assertEqual(parsed.id, original.id)
        self.assertEqual(parsed.ts, original.ts)
        self.assertEqual(parsed.tick, original.tick)
        self.assertEqual(parsed.correlation_id, original.correlation_id)

    def test_round_trip_all_types(self):
        """Round-trip works for all five message types."""
        classes = [ActionMessage, EventMessage, CommandMessage, ToolMessage, StreamMessage]
        for cls in classes:
            original = cls(source="test", name="test", payload={"key": "value"})
            parsed = parse_message(original.to_dict())
            self.assertIsInstance(parsed, cls, f"Round-trip failed for {cls.__name__}")
            self.assertEqual(parsed.type, original.type)


# ── Message alias compatibility ─────────────────────────────────────────────


class TestMessageAlias(unittest.TestCase):
    """Verify that the Message alias still works for backward compatibility."""

    def test_message_alias_is_base_message(self):
        self.assertIs(Message, BaseMessage)

    def test_message_alias_can_construct(self):
        msg = Message(source="test", type="action", name="test", payload={})
        self.assertEqual(msg.type, "action")
