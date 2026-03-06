# Quickstart: Pydantic Discriminated Unions for Messages

## Creating Messages

### Using Typed Constructors (Preferred)

```python
from app.protocol import ActionMessage, EventMessage, CommandMessage

# Action message
msg = ActionMessage(source="rover", name="move", payload={"direction": "north"})
assert msg.type == "action"  # Automatically set, immutable

# Event message
msg = EventMessage(source="world", name="state", payload={"tick": 42})
assert msg.type == "event"

# Command message
msg = CommandMessage(source="station", name="assign_mission", payload={"agent_id": "rover-1"})
assert msg.type == "command"
```

### Using the Factory Function

```python
from app.protocol import make_message

# Returns the appropriate typed subclass
msg = make_message("rover", "action", "move", {"direction": "north"})
assert isinstance(msg, ActionMessage)
```

## Serializing Messages

```python
# to_dict() produces the same output as the old dataclass asdict()
msg_dict = msg.to_dict()
# {"source": "rover", "type": "action", "name": "move", "payload": {...}, "id": "...", ...}

# Send over WebSocket
await ws.send_json(msg.to_dict())
```

## Parsing Messages

```python
from app.protocol import parse_message

# Parse a raw dictionary into the correct typed model
data = {"source": "rover", "type": "action", "name": "move", "payload": {}, "id": "...", "ts": 1.0, "tick": 0}
msg = parse_message(data)
assert isinstance(msg, ActionMessage)
```

## Running Tests

```bash
cd server
uv run pytest tests/test_protocol.py -v
```
