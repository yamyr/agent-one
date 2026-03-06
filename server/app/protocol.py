"""Host-Agent protocol: typed message envelope for all Host ↔ Agent exchanges.

Uses Pydantic v2 discriminated unions for type-safe message construction.
Five message types (action, event, command, tool, stream) each have a typed
subclass with a Literal discriminator on the ``type`` field.
"""

import time
import uuid
from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

from .world import world as default_world


class MessageType(StrEnum):
    """Enumeration of the five valid message type values."""

    ACTION = "action"
    EVENT = "event"
    COMMAND = "command"
    TOOL = "tool"
    STREAM = "stream"


class BaseMessage(BaseModel):
    """Base message envelope for Host ↔ Agent communication.

    Every exchange has a unique id, timestamp, tick, source, type, name,
    payload, and optional correlation_id linking responses to triggers.

    Do not instantiate directly — use a typed subclass or ``make_message()``.
    """

    source: str
    type: str
    name: str
    payload: dict[str, Any]
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = Field(default_factory=time.time)
    tick: int = Field(default_factory=lambda: default_world.get_tick())
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON / WebSocket transport."""
        return self.model_dump()


# ── Typed message subclasses ────────────────────────────────────────────────


class ActionMessage(BaseMessage):
    """Message with type locked to ``"action"``."""

    type: Literal["action"] = "action"


class EventMessage(BaseMessage):
    """Message with type locked to ``"event"``."""

    type: Literal["event"] = "event"


class CommandMessage(BaseMessage):
    """Message with type locked to ``"command"``."""

    type: Literal["command"] = "command"


class ToolMessage(BaseMessage):
    """Message with type locked to ``"tool"``."""

    type: Literal["tool"] = "tool"


class StreamMessage(BaseMessage):
    """Message with type locked to ``"stream"``."""

    type: Literal["stream"] = "stream"


# ── Discriminated union type ────────────────────────────────────────────────

AnyMessage = Annotated[
    Union[ActionMessage, EventMessage, CommandMessage, ToolMessage, StreamMessage],
    Field(discriminator="type"),
]

# ── Backward-compatible alias ───────────────────────────────────────────────

Message = BaseMessage
"""Alias kept for import compatibility with existing code."""

# ── Factory functions ───────────────────────────────────────────────────────

_TYPE_TO_CLASS: dict[str, type[BaseMessage]] = {
    "action": ActionMessage,
    "event": EventMessage,
    "command": CommandMessage,
    "tool": ToolMessage,
    "stream": StreamMessage,
}


def make_message(
    source: str,
    type: str,
    name: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> BaseMessage:
    """Factory that creates a typed Message with auto-stamped id, ts, and tick.

    Dispatches on *type* to return the appropriate typed subclass.
    Falls back to BaseMessage for unknown types (defensive).
    """
    cls = _TYPE_TO_CLASS.get(type, BaseMessage)
    return cls(
        source=source,
        name=name,
        payload=payload,
        correlation_id=correlation_id,
    )


def parse_message(data: dict[str, Any]) -> BaseMessage:
    """Deserialize a raw dictionary into the correct typed message model.

    Uses Pydantic's TypeAdapter with the AnyMessage discriminated union
    to resolve the correct subclass based on the ``type`` field.
    """
    from pydantic import TypeAdapter

    adapter = TypeAdapter(AnyMessage)
    return adapter.validate_python(data)
