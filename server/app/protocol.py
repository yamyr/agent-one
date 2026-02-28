"""Host-Agent protocol: typed message envelope for all Host ↔ Agent exchanges."""

import time
import uuid
from dataclasses import dataclass, field, asdict

from .world import WORLD


@dataclass
class Message:
    """Typed message envelope for Host ↔ Agent communication.

    Every exchange has a unique id, timestamp, tick, source, type, name,
    payload, and optional correlation_id linking responses to triggers.
    """

    source: str
    type: str
    name: str
    payload: dict
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = field(default_factory=time.time)
    tick: int = field(default_factory=lambda: WORLD["tick"])
    correlation_id: str | None = None

    def to_dict(self):
        """Serialize to a plain dict for JSON / WebSocket transport."""
        return asdict(self)


def make_message(source, type, name, payload, correlation_id=None):
    """Factory that creates a Message with auto-stamped id, ts, and tick."""
    return Message(
        source=source,
        type=type,
        name=name,
        payload=payload,
        correlation_id=correlation_id,
    )
