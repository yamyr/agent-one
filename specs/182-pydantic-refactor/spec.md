# Feature Specification: Pydantic Refactor — Discriminated Unions & Model Validators

**Feature Branch**: `182-pydantic-refactor`
**Created**: 2026-03-05
**Status**: Draft
**Input**: User description: "Pydantic Refactor — Discriminated Unions & Model Validators"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Typed Message Protocol (Priority: P1)

As a developer working on the simulation, I want all protocol messages to use discriminated union types so that I can statically verify message correctness and catch protocol errors at parse time rather than at runtime.

**Why this priority**: Message types are the communication backbone of the entire agent system. Every agent, the host, and the broadcaster create and consume messages. Typing these correctly eliminates the largest class of runtime protocol errors and unlocks IDE autocompletion for payload fields.

**Independent Test**: Can be fully tested by constructing messages of each type and verifying that invalid type/name combinations are rejected at model creation time. Delivers immediate value through parse-time validation and IDE support.

**Acceptance Scenarios**:

1. **Given** a message with type "event" and name "move", **When** the message is constructed, **Then** it is validated as a valid EventMessage with the correct payload structure.
2. **Given** a message with an unknown type value, **When** parsed into the union type, **Then** a validation error is raised immediately.
3. **Given** a valid message dict from WebSocket, **When** deserialized, **Then** the correct discriminated subtype is returned automatically based on the type field.
4. **Given** existing code that creates messages via `make_message()`, **When** the refactor is applied, **Then** all existing call sites still produce valid typed messages without behavior changes.

---

### User Story 2 - Model Validators for World State Consistency (Priority: P2)

As a developer, I want model validators on agent state and world models so that invalid state (e.g., negative battery, out-of-bounds positions) is caught immediately when models are constructed rather than causing silent corruption downstream.

**Why this priority**: Without validators, invalid state propagates silently through the system — a battery of -0.3 or a position of [-5, 200] on a 30x30 grid would not be caught until it causes a visible bug. Validators provide a safety net at the model boundary.

**Independent Test**: Can be tested by constructing models with boundary and invalid values and verifying that validators clamp or reject appropriately. Delivers value through early error detection.

**Acceptance Scenarios**:

1. **Given** a battery value of 1.5, **When** constructing an agent state model, **Then** the value is clamped to 1.0.
2. **Given** a battery value of -0.2, **When** constructing an agent state model, **Then** the value is clamped to 0.0.
3. **Given** a position of [-1, 50] on a 30x30 grid, **When** constructing a model that validates position, **Then** the position is clamped to valid grid bounds [0, 29].
4. **Given** a goal_confidence of 2.0, **When** constructing an agent state model, **Then** the value is clamped to 1.0.
5. **Given** valid values within all bounds, **When** constructing any model, **Then** the model is created without modification (no false positives).

---

### User Story 3 - Typed ResourceDeposit Model (Priority: P3)

As a developer, I want resource deposits to use the existing ResourceType enum in a typed ResourceDeposit model so that resource handling is consistent and type-safe across the codebase.

**Why this priority**: The ResourceType enum already exists but resource deposits in the world state use plain dicts with string type fields. Wrapping these in a typed model ensures consistency and prevents typos in resource type strings.

**Independent Test**: Can be tested by constructing ResourceDeposit models with valid and invalid resource types and verifying enum enforcement. Delivers value through consistent resource typing.

**Acceptance Scenarios**:

1. **Given** a resource deposit with type "basalt_vein", **When** constructed as a ResourceDeposit, **Then** the type field is a valid ResourceType enum member.
2. **Given** a resource deposit with type "unknown_mineral", **When** constructed as a ResourceDeposit, **Then** a validation error is raised.
3. **Given** existing stone and ice deposit data in the world state, **When** the refactor is applied, **Then** all existing deposits are representable with the new typed model.

---

### User Story 4 - Updated Call Sites (Priority: P4)

As a developer, I want all message creation and consumption call sites in agent.py, host.py, and station.py to use the new typed models so that the entire message pipeline is type-safe end-to-end.

**Why this priority**: The typed models only deliver full value when all producers and consumers use them. This story ensures no call site is left using raw dicts for message construction.

**Independent Test**: Can be tested by running the full test suite after updating call sites — all existing tests must pass, confirming behavioral equivalence. Additionally, static type checking should report zero type errors in the updated files.

**Acceptance Scenarios**:

1. **Given** a rover agent producing a "move" action message, **When** the call site uses the typed model, **Then** the message is constructed with payload validation.
2. **Given** the host broadcasting a message, **When** it receives a typed message, **Then** serialization to dict for WebSocket works identically to the current behavior.
3. **Given** the station agent handling an event, **When** the event is deserialized, **Then** the correct typed message subclass is returned.
4. **Given** the entire test suite, **When** run after all call site updates, **Then** all tests pass with zero regressions.

---

### Edge Cases

- What happens when a message has a valid type but an unexpected payload shape? Validators should reject with a clear error.
- What happens when legacy/persisted messages (e.g., in training logs) are loaded with the new types? The system should handle missing fields gracefully with defaults.
- What happens when a new message type is added in the future? The discriminated union should be easily extensible by adding a new subclass.
- What happens when battery is exactly 0.0 or 1.0? Boundary values must be accepted, not rejected.
- What happens when position is at grid edges (0 or grid_size-1)? These are valid and must pass validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define discriminated union types for all protocol message categories (event, action, command, tool, stream) using a type discriminator field.
- **FR-002**: The system MUST validate message payloads against the expected schema for each message type at construction time.
- **FR-003**: The system MUST provide model validators for battery values, clamping to the [0.0, 1.0] range.
- **FR-004**: The system MUST provide model validators for goal_confidence values, clamping to the [0.0, 1.0] range.
- **FR-005**: The system MUST provide model validators for position coordinates, clamping to valid grid bounds.
- **FR-006**: The system MUST use the existing ResourceType enum in a typed ResourceDeposit model for all resource deposit representations.
- **FR-007**: All message creation call sites in agent.py, host.py, and station.py MUST use typed message models instead of raw dict construction.
- **FR-008**: The system MUST maintain full backward compatibility — all existing tests must pass without modification after the refactor.
- **FR-009**: The system MUST support serialization of typed messages to plain dicts for WebSocket broadcast compatibility.
- **FR-010**: The system MUST support deserialization of plain dicts back into the correct discriminated union subtype.

### Key Entities

- **Message**: The base protocol unit with fields: id, ts, source, type, name, payload, tick, correlation_id. Discriminated by the `type` field into subtypes (EventMessage, ActionMessage, CommandMessage, ToolMessage, StreamMessage).
- **AgentState**: Per-agent state with validated fields: position (grid-bounded), battery (0.0-1.0), goal_confidence (0.0-1.0), inventory, mission, memory.
- **ResourceDeposit**: A typed resource occurrence in the world, combining position, quantity, and a ResourceType enum value.
- **ResourceType**: Existing enum with values: basalt_vein, ice, water, gas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of protocol message types are covered by discriminated union subtypes — no message is constructed as an untyped dict.
- **SC-002**: All agent state models include validators for numeric bounds (battery, goal_confidence) and spatial bounds (position) — zero invalid states can be constructed.
- **SC-003**: All existing tests pass after the refactor with zero regressions — the change is purely additive in safety, not behavioral.
- **SC-004**: All resource deposits in the world state use the typed ResourceDeposit model with ResourceType enum enforcement.
- **SC-005**: New tests achieve at least 90% coverage of the new validator and discriminated union logic.
- **SC-006**: Invalid message construction (wrong type, out-of-bounds values) is caught at model creation time, not at runtime consumption.

## Assumptions

- The existing `@dataclass Message` in protocol.py will be migrated to a Pydantic BaseModel to enable discriminated unions and validators. This is a necessary prerequisite since dataclasses do not support discriminator features.
- Position validators will use the grid dimensions from the world configuration (currently 30x30) as the bounds reference.
- Battery and goal_confidence validators will use clamping behavior (silently adjust to valid range) rather than rejection behavior (raise error), since the simulation already produces boundary-adjacent values during normal operation.
- The `make_message()` factory function will be updated to return typed message instances, but a `.model_dump()` method will preserve WebSocket serialization compatibility.
- Training log compatibility: existing training data files with old message formats will not be retroactively migrated; the new models will accept legacy formats via default field values.
