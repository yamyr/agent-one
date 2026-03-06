# Tasks: Pydantic Discriminated Unions for Messages

**Input**: Design documents from `/specs/190-pydantic-discriminated-unions/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: Included (spec explicitly requires comprehensive tests -- FR-010, SC-001 through SC-006).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Server**: `server/app/` for application code, `server/tests/` for tests

---

## Phase 1: Setup

**Purpose**: Verify Pydantic v2 is available and understand current protocol usage

- [x] T001 Verify pydantic v2 is available in server dependencies by checking `server/pyproject.toml`

---

## Phase 2: Foundational (Core Models in protocol.py)

**Purpose**: Define BaseMessage, MessageType enum, all five typed subclasses, AnyMessage union, and factory functions in `server/app/protocol.py`. This MUST be complete before any call site updates or tests.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Replace the `Message` dataclass with `MessageType` enum, `BaseMessage` Pydantic BaseModel, five typed subclasses (`ActionMessage`, `EventMessage`, `CommandMessage`, `ToolMessage`, `StreamMessage`), `AnyMessage` discriminated union type, `parse_message()` factory, and updated `make_message()` factory in `server/app/protocol.py`. Preserve backward-compatible `to_dict()` method using `model_dump()`. Keep `Message` as an alias for `BaseMessage` for import compatibility.

**Checkpoint**: protocol.py now exports all new types. Existing `make_message()` calls still work.

---

## Phase 3: User Story 1 & 2 - Type-Safe Construction + Backward-Compatible Serialization (P1)

**Goal**: All typed message constructors work correctly AND serialization output is identical to previous dataclass format.

**Independent Test**: Create messages with each typed constructor, verify type field is correct and immutable, verify `to_dict()` output matches previous `asdict()` structure.

### Tests for US1 & US2

- [x] T003 [US1] Write tests in `server/tests/test_protocol.py` for: (a) each typed constructor sets correct literal type, (b) all five message types can be instantiated with required fields, (c) auto-generated fields (id, ts, tick) are populated, (d) correlation_id defaults to None, (e) invalid type override raises validation error
- [x] T004 [US2] Write tests in `server/tests/test_protocol.py` for: (a) `to_dict()` output has exactly the same keys as old `asdict()` (id, ts, tick, source, type, name, payload, correlation_id), (b) `to_dict()` output is JSON-serializable, (c) correlation_id=None is present in output, (d) empty payload `{}` serializes correctly, (e) deeply nested payload serializes correctly
- [x] T005 [P] [US1] Write tests in `server/tests/test_protocol.py` for `make_message()` factory: (a) returns correct typed subclass based on type string, (b) preserves all arguments, (c) unique IDs per call

**Checkpoint**: All construction and serialization tests pass. The core models are proven correct.

---

## Phase 4: User Story 3 - Message Deserialization with Discriminator (P2)

**Goal**: `parse_message()` factory correctly resolves raw dicts into typed models using the discriminator.

**Independent Test**: Create raw dicts with each type value, call `parse_message()`, verify correct subclass returned.

### Tests for US3

- [x] T006 [US3] Write tests in `server/tests/test_protocol.py` for `parse_message()`: (a) raw dict with type="action" returns ActionMessage, (b) type="event" returns EventMessage, (c) type="command" returns CommandMessage, (d) type="tool" returns ToolMessage, (e) type="stream" returns StreamMessage, (f) invalid type="unknown" raises ValidationError, (g) missing required fields raises ValidationError, (h) extra fields are ignored, (i) round-trip: create message -> to_dict() -> parse_message() produces equivalent instance

**Checkpoint**: Deserialization is proven correct for all types including error cases.

---

## Phase 5: User Story 4 - Updated Call Sites (P1)

**Goal**: All existing `make_message()` and `Message()` call sites use the typed constructors or updated factory. No untyped `Message()` instantiation remains.

**Independent Test**: Full test suite passes after migration.

### Implementation for US4

- [x] T007 [US4] Update `server/app/agent.py`: replace all `make_message()` imports and calls to use the new typed protocol. Ensure the import comes from `.protocol` and `make_message()` returns typed subclasses.
- [x] T008 [P] [US4] Update `server/app/host.py`: replace all `make_message()` calls. The function signature is unchanged so updates are mechanical -- verify each call site passes correct type string.
- [x] T009 [P] [US4] Update `server/app/views.py`: replace `make_message()` usage and verify `to_dict()` calls remain unchanged.
- [x] T010 [P] [US4] Update `server/app/main.py`: replace the two `from .protocol import make_message` local imports and all `make_message()` calls.
- [x] T011 [US4] Update `server/tests/test_protocol.py`: update existing `TestMessage` and `TestMakeMessage` test classes to import from the new typed models. Update `Message(...)` direct instantiations to use typed constructors (e.g., `ActionMessage(...)`, `EventMessage(...)`). Keep test assertions unchanged.

**Checkpoint**: Full test suite passes. `grep -r "Message(" server/` shows no untyped Message instantiation outside of protocol.py itself.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, formatting, and cleanup

- [x] T012 Run `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/` to ensure code passes linting
- [x] T013 Run `cd server && uv run pytest tests/ -x -q` to verify full test suite passes
- [x] T014 Update `Changelog.md` with the changes from this feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **US1 & US2 (Phase 3)**: Depends on Phase 2 - core model tests
- **US3 (Phase 4)**: Depends on Phase 2 - deserialization tests
- **US4 (Phase 5)**: Depends on Phase 2 - call site migration
- **Polish (Phase 6)**: Depends on all previous phases

### User Story Dependencies

- **US1 + US2 (P1)**: Can start after Phase 2 - No cross-story dependencies
- **US3 (P2)**: Can start after Phase 2 - Independent of US1/US2
- **US4 (P1)**: Can start after Phase 2 - Independent of US1/US2/US3 (but tests from US1/US2 validate correctness)

### Within Each Phase

- Tests written before implementation verification
- Models before services
- Core protocol changes before call site updates

### Parallel Opportunities

- Phase 3 (US1+US2 tests) and Phase 4 (US3 tests) can run in parallel after Phase 2
- Within Phase 5: T008, T009, T010 can run in parallel (different files)
- T003, T004, T005 write to the same test file but different test classes -- execute sequentially

---

## Parallel Example: Phase 5 Call Site Updates

```bash
# These can run in parallel (different files, no dependencies):
Task T008: "Update server/app/host.py"
Task T009: "Update server/app/views.py"
Task T010: "Update server/app/main.py"
```

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + 3)

1. Complete Phase 1: Verify dependencies
2. Complete Phase 2: Build core models in protocol.py
3. Complete Phase 3: Prove construction and serialization with tests
4. **STOP and VALIDATE**: Run tests, verify backward compatibility

### Full Delivery

1. Complete Phases 1-3 (MVP)
2. Complete Phase 4: Deserialization tests
3. Complete Phase 5: Migrate all call sites
4. Complete Phase 6: Polish, lint, full test suite, changelog

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- The `make_message()` factory is retained -- call sites that use it need minimal changes
- `Message` is kept as an alias to `BaseMessage` for import compatibility in tests
- Commit after each phase completion
- The primary risk is serialization incompatibility -- Phase 3 tests catch this early
