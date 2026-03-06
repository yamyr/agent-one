# Data Model: Pydantic Discriminated Unions for Messages

## Entities

### MessageType (Enum)

| Value     | Description                          |
|-----------|--------------------------------------|
| action    | Agent action results                 |
| event     | System/world events                  |
| command   | Commands between agents or from host |
| tool      | Tool call results                    |
| stream    | Streaming data chunks                |

### BaseMessage (Pydantic BaseModel)

| Field          | Type             | Default                    | Description                                |
|----------------|------------------|----------------------------|--------------------------------------------|
| source         | str              | (required)                 | Origin identifier (e.g., "rover", "world") |
| type           | str              | (required)                 | Message type discriminator                 |
| name           | str              | (required)                 | Message name/action name                   |
| payload        | dict[str, Any]   | (required)                 | Message data (untyped for now)             |
| id             | str              | uuid4()                    | Unique message identifier                  |
| ts             | float            | time.time()                | Unix timestamp                             |
| tick           | int              | world.get_tick()           | Simulation tick at creation                |
| correlation_id | str or None      | None                       | Links response to trigger message          |

### Typed Message Subclasses

| Class          | type Literal   | Inherits From |
|----------------|----------------|---------------|
| ActionMessage  | "action"       | BaseMessage   |
| EventMessage   | "event"        | BaseMessage   |
| CommandMessage | "command"      | BaseMessage   |
| ToolMessage    | "tool"         | BaseMessage   |
| StreamMessage  | "stream"       | BaseMessage   |

### AnyMessage (Union Type)

Discriminated union of all five typed subclasses, using `type` as the discriminator field.

```
AnyMessage = Annotated[
    ActionMessage | EventMessage | CommandMessage | ToolMessage | StreamMessage,
    Field(discriminator="type")
]
```

## Relationships

- Each typed message subclass IS-A BaseMessage with a fixed `type` literal.
- AnyMessage is a UNION-OF all five typed subclasses.
- `make_message()` factory PRODUCES the appropriate typed subclass based on the `type` argument.
- `parse_message()` factory DESERIALIZES a raw dict into the appropriate typed subclass.

## Validation Rules

- `source`: Non-empty string
- `type`: Must be one of the five MessageType values (enforced by Literal)
- `name`: Non-empty string
- `payload`: Any dict (no further validation in this iteration)
- `id`: Auto-generated UUID string, should not be manually set to empty
- `ts`: Auto-generated float timestamp
- `tick`: Auto-generated integer from world state
- `correlation_id`: Optional, None by default

## Serialization

`to_dict()` method on all models calls `model_dump()` and produces:

```json
{
    "source": "rover",
    "type": "action",
    "name": "move",
    "payload": {"direction": "north"},
    "id": "uuid-string",
    "ts": 1709234567.123,
    "tick": 42,
    "correlation_id": null
}
```

This is structurally identical to the previous `dataclasses.asdict()` output.
