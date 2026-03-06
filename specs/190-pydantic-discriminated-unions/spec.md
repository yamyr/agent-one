# Feature Specification: Pydantic Discriminated Unions for Messages

**Feature Branch**: `190-pydantic-discriminated-unions`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "Convert the current protocol Message dataclass into Pydantic models with discriminated unions for type safety. Create MessageType enum, typed message subclasses with Literal discriminators on the type field, AnyMessage union type, and parse_message() factory. Keep payload as dict. Update all call sites. Maintain backward-compatible to_dict() output."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type-Safe Message Construction (Priority: P1)

As a developer working on the Mars simulation backend, I want to create messages using typed constructors (e.g., ActionMessage, EventMessage) so that the type field is automatically set correctly and cannot be misspelled or mismatched.

**Why this priority**: This is the core value proposition. Type-safe constructors prevent an entire class of bugs where message types are misspelled or inconsistent, and enable IDE autocompletion and static analysis.

**Independent Test**: Can be fully tested by creating messages with each typed constructor and verifying that the type field is always set to the correct literal value.

**Acceptance Scenarios**:

1. **Given** a developer needs to create an action message, **When** they instantiate `ActionMessage(source="rover", name="move", payload={"direction": "north"})`, **Then** the resulting message has `type="action"` automatically and cannot be overridden to an invalid value.
2. **Given** a developer creates a message with the typed constructor, **When** they serialize it with `to_dict()`, **Then** the output contains all expected fields (id, ts, tick, source, type, name, payload, correlation_id) in the same structure as before.
3. **Given** any of the five message types (action, event, command, tool, stream), **When** a developer creates the corresponding typed message, **Then** the type field is locked to the correct literal value.

---

### User Story 2 - Backward-Compatible Serialization (Priority: P1)

As the WebSocket transport layer, I need serialized messages to produce the exact same JSON structure as the current dataclass-based messages so that existing UI clients continue to work without any changes.

**Why this priority**: Breaking the WebSocket protocol would disrupt the entire frontend application. Zero-downtime compatibility is critical.

**Independent Test**: Can be tested by creating messages with the new typed constructors, serializing them, and comparing the output structure field-by-field against the previous dataclass serialization.

**Acceptance Scenarios**:

1. **Given** a message created with the new Pydantic model, **When** `to_dict()` is called, **Then** the output dictionary has exactly the same keys as the previous dataclass `asdict()` output: id, ts, tick, source, type, name, payload, correlation_id.
2. **Given** a serialized message dictionary, **When** it is sent over WebSocket to the UI, **Then** the UI processes it identically to messages from the old system.
3. **Given** a message with correlation_id=None, **When** serialized, **Then** the correlation_id key is present with value None (matching previous behavior).

---

### User Story 3 - Message Deserialization with Discriminator (Priority: P2)

As a system component receiving messages from external sources or storage, I want to parse a raw dictionary back into the correct typed message model so that I can leverage type safety when processing incoming messages.

**Why this priority**: Parsing enables round-trip safety and future use cases like message replay, logging, and testing.

**Independent Test**: Can be tested by creating raw dictionaries with different type values and verifying that `parse_message()` returns the correctly-typed model instance.

**Acceptance Scenarios**:

1. **Given** a raw dictionary with `type="action"`, **When** `parse_message(data)` is called, **Then** the result is an instance of ActionMessage.
2. **Given** a raw dictionary with `type="event"`, **When** `parse_message(data)` is called, **Then** the result is an instance of EventMessage.
3. **Given** a raw dictionary with an invalid type value (e.g., `type="unknown"`), **When** `parse_message(data)` is called, **Then** a validation error is raised.

---

### User Story 4 - Updated Call Sites (Priority: P1)

As the codebase maintainer, I need all existing `make_message()` and `Message()` call sites updated to use the appropriate typed constructors so that the migration is complete and the old untyped constructor is eliminated.

**Why this priority**: Leaving old call sites would defeat the purpose of type safety and create inconsistency.

**Independent Test**: Can be tested by running the full test suite after migration and verifying all tests pass with the new constructors.

**Acceptance Scenarios**:

1. **Given** an existing call like `make_message("rover", "action", "move", {...})`, **When** the migration is complete, **Then** it uses a typed factory that produces an ActionMessage.
2. **Given** the full test suite, **When** run after migration, **Then** all tests pass without modification to test assertions (only constructors change).

---

### Edge Cases

- What happens when a message is created with an empty payload (`{}`)? The system must accept it without error.
- What happens when a message is created with deeply nested payload data? Serialization must handle arbitrary nesting.
- What happens when `parse_message()` receives a dictionary missing required fields? A clear validation error must be raised.
- What happens when `parse_message()` receives extra fields not in the model? They should be ignored gracefully.
- What happens when the world tick provider is unavailable? The default tick value should still work.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define a MessageType enumeration with exactly five values: action, event, command, tool, stream.
- **FR-002**: System MUST provide a base message model with fields: source (string), type (string literal), name (string), payload (dictionary), id (auto-generated UUID string), ts (auto-generated timestamp), tick (auto-generated from world tick), and correlation_id (optional string).
- **FR-003**: System MUST provide five typed message subclasses (ActionMessage, EventMessage, CommandMessage, ToolMessage, StreamMessage), each with the type field locked to its corresponding literal value.
- **FR-004**: System MUST provide a union type (AnyMessage) that uses the type field as a discriminator for automatic type resolution.
- **FR-005**: System MUST provide a `parse_message(data: dict)` factory function that accepts a raw dictionary and returns the correctly-typed message instance using the discriminator.
- **FR-006**: System MUST provide a `to_dict()` method on all message models that produces output identical in structure to the previous dataclass `asdict()` serialization.
- **FR-007**: System MUST maintain the `make_message()` factory function for backward compatibility, returning the appropriate typed message subclass based on the type argument.
- **FR-008**: System MUST update all existing call sites that create messages to use the typed constructors or the updated `make_message()` factory.
- **FR-009**: System MUST keep payload typed as `dict[str, Any]` (not further constrained) for this iteration.
- **FR-010**: System MUST raise validation errors when a message is created with an invalid type value or missing required fields.

### Key Entities

- **BaseMessage**: Core message model with all common fields (id, ts, tick, source, name, payload, correlation_id). Not instantiated directly.
- **ActionMessage / EventMessage / CommandMessage / ToolMessage / StreamMessage**: Typed subclasses with the type field constrained to a specific literal value.
- **AnyMessage**: Union type enabling discriminated parsing across all five message types.
- **MessageType**: Enumeration of the five valid message type values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five message type constructors produce messages with the correct, immutable type field value.
- **SC-002**: Serialized output from `to_dict()` is structurally identical to the previous dataclass serialization for all message types.
- **SC-003**: `parse_message()` correctly resolves all five message types from raw dictionaries.
- **SC-004**: 100% of existing tests pass after migration without changes to test assertions.
- **SC-005**: Invalid message type values are rejected at construction time with clear error messages.
- **SC-006**: All call sites in the codebase use typed constructors — no untyped Message() instantiation remains.

## Assumptions

- Pydantic v2 is already available in the project dependencies (confirmed: pydantic-settings is used).
- The `payload` field will remain as `dict[str, Any]` — full payload typing is a future enhancement.
- The `ts` field will continue using `time.time()` (float) for timestamp generation to maintain backward compatibility.
- The `tick` field will continue using the world's `get_tick()` default factory.
- WebSocket consumers (UI) only read the serialized dictionary — they do not depend on Python-level types.
