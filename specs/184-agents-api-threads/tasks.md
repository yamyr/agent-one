# Tasks: Agents API — Persistent Conversation Threads + Training Logger

**Input**: Design documents from `/specs/184-agents-api-threads/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included (spec explicitly requests tests for thread persistence and training logger).

**Organization**: Tasks grouped by user story (US1: Threads, US2: Training Logger, US3: Config Toggle).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Config Foundation)

**Purpose**: Add the config setting that US1 and US3 both depend on

- [X] T001 Add `agents_api_persist_threads: bool = True` to Settings class in `server/app/config.py`

**Checkpoint**: Config field available for use by reasoners

---

## Phase 2: User Story 1 — Persistent Conversation Threads (Priority: P1)

**Goal**: All 3 Agents API reasoners maintain conversation threads across turns using `conversations.append()`

**Independent Test**: `cd server && uv run pytest tests/ -v -k "conversation_thread"`

### Tests for User Story 1

- [X] T002 [P] [US1] Write test `test_rover_conversation_thread_persists` — verify first turn calls `start()`, second turn calls `append()` with stored conversation_id, in `server/tests/test_agents_api.py`
- [X] T003 [P] [US1] Write test `test_drone_conversation_thread_persists` — same pattern for drone reasoner, in `server/tests/test_agents_api.py`
- [X] T004 [P] [US1] Write test `test_station_conversation_thread_persists` — same pattern for station reasoner, in `server/tests/test_agents_api.py`
- [X] T005 [P] [US1] Write test `test_conversation_id_cleared_on_new_instance` — new reasoner instance has `_conversation_id = None`, in `server/tests/test_agents_api.py`

### Implementation for User Story 1

- [X] T006 [P] [US1] Add `self._conversation_id = None` to `AgentsApiRoverReasoner.__init__()` and update `run_turn()` to use `start()`/`append()` switching in `server/app/agents_api.py`
- [X] T007 [P] [US1] Add `self._conversation_id = None` to `AgentsApiDroneReasoner.__init__()` and update `run_turn()` to use `start()`/`append()` switching in `server/app/agents_api.py`
- [X] T008 [P] [US1] Add `self._conversation_id = None` to `AgentsApiStationReasoner.__init__()` and update `run_turn()` to use `start()`/`append()` switching in `server/app/agents_api.py`

**Checkpoint**: All 3 reasoners persist threads; tests pass

---

## Phase 3: User Story 2 — Training Logger Integration (Priority: P1)

**Goal**: Remove misleading `# TODO` comment; verify training logging works via Loop inheritance

**Independent Test**: `cd server && uv run pytest tests/ -v -k "agents_api_training"`

### Tests for User Story 2

- [X] T009 [US2] Write test `test_agents_api_training_logger_wired` — verify `RoverAgentsApiLoop` inherits `tick()` from `RoverLoop` which calls training logger, in `server/tests/test_agents_api.py`

### Implementation for User Story 2

- [X] T010 [US2] Remove `# TODO: integrate training logger` comment at line 113 of `server/app/agents_api.py`

**Checkpoint**: TODO removed; test confirms training logger is wired via inheritance

---

## Phase 4: User Story 3 — Config Toggle for Thread Persistence (Priority: P2)

**Goal**: `agents_api_persist_threads` setting controls whether threads are reused or each turn starts fresh

**Independent Test**: `cd server && uv run pytest tests/ -v -k "persist_threads"`

### Tests for User Story 3

- [X] T011 [US3] Write test `test_persist_threads_false_always_starts_new` — when setting is False, every turn calls `start()` (conversation_id not stored), in `server/tests/test_agents_api.py`

### Implementation for User Story 3

- [X] T012 [US3] Ensure `run_turn()` in all 3 reasoners checks `settings.agents_api_persist_threads` before storing/using `_conversation_id` in `server/app/agents_api.py` (may already be done in T006-T008)

**Checkpoint**: Config toggle works; tests pass

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T013 Run full test suite: `cd server && uv run pytest tests/ -v`
- [X] T014 Run ruff format and lint: `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/`
- [X] T015 Update `Changelog.md` with feature entries

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends on T001 (config setting)
- **Phase 3 (US2)**: Independent of US1 — can run in parallel
- **Phase 4 (US3)**: Depends on US1 implementation (T006-T008) since it tests the persist toggle behavior
- **Phase 5 (Polish)**: Depends on all user stories complete

### Parallel Opportunities

- T002, T003, T004, T005 can all run in parallel (test stubs)
- T006, T007, T008 can all run in parallel (different classes, same file but different sections)
- T009 and T010 can run in parallel with US1 tasks
- T013, T014, T015 can run in parallel

### Parallel Example: US1 Implementation

```bash
# Launch all 3 reasoner updates together:
Task: "Update AgentsApiRoverReasoner in agents_api.py"
Task: "Update AgentsApiDroneReasoner in agents_api.py"
Task: "Update AgentsApiStationReasoner in agents_api.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. T001: Config setting
2. T002-T005: Write thread persistence tests (parallel)
3. T006-T008: Implement thread persistence in all 3 reasoners (parallel)
4. T009-T010: Training logger verification + TODO removal
5. **VALIDATE**: Run tests

### Complete Delivery

6. T011-T012: Config toggle tests + verification
7. T013-T015: Full test suite, lint, changelog

---

## Notes

- All changes are in 3 files: `agents_api.py`, `config.py`, `test_agents_api.py`
- The 3 reasoner classes have identical patterns — changes are mechanical and parallel
- `_parse_conversation_response()` works unchanged for both `start()` and `append()` responses
- Total: 15 tasks, 8 parallelizable
