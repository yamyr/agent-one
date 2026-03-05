# Tasks: Human-in-the-Loop (UiRequest::Confirm)

**Input**: Design documents from `/specs/183-human-in-the-loop/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, contracts/websocket-message-schema.md, quickstart.md

**Tests**: Included — the CLAUDE.md requires complete test coverage before PR.

**Organization**: Tasks grouped by user story derived from feature scope.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project initialization needed. This feature extends an existing codebase. Phase 1 is skipped — the project structure is already in place.

**Checkpoint**: No changes needed. Proceed to Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Host confirmation infrastructure that US1 (tool execution) and US2 (endpoint) both depend on.

- [X] T001 [P] Create test file `server/tests/test_confirm.py` with TestHostConfirmation class (8 tests: create returns UUID, resolve sets response and signals event, get retrieves by request_id, get_agent retrieves by agent_id, cleanup removes entry, one-per-agent limit enforced, resolve nonexistent returns False, CONFIRM_DEFAULT_TIMEOUT constant exists)
- [X] T002 Add `CONFIRM_DEFAULT_TIMEOUT = 30` constant and initialize `_pending_confirms = {}` dict in `Host.__init__()` in `server/app/host.py`
- [X] T003 Implement `create_confirm(agent_id, question, timeout)`, `resolve_confirm(request_id, confirmed)`, `get_pending_confirm(request_id)`, `get_agent_pending_confirm(agent_id)`, and `cleanup_confirm(request_id)` methods in Host class in `server/app/host.py`

**Checkpoint**: Host can create, resolve, query, and clean up pending confirmations. Tests pass in isolation.

---

## Phase 3: User Story 1 — Rover Request Confirm Tool (Priority: P1)

**Goal**: Rover has a `request_confirm` tool that pauses its loop and emits a `confirm_request` event.

**Independent Test**: `uv run pytest tests/test_confirm.py -v -k "TestRequestConfirmTool"`

### Tests for User Story 1

- [X] T004 [P] [US1] Add TestRequestConfirmTool class to `server/tests/test_confirm.py` (6 tests: tool schema has correct name/params/description, tool present in ROVER_TOOLS list, request emits confirm_request event with correct payload, request blocks until response received, timeout treated as denied, timeout emits confirm_timeout event)

### Implementation for User Story 1

- [X] T005 [US1] Define `REQUEST_CONFIRM_TOOL` dict in `server/app/agent.py` after existing rover tool definitions (~line 330)
- [X] T006 [US1] Add `REQUEST_CONFIRM_TOOL` to the `ROVER_TOOLS` list in `server/app/agent.py`
- [X] T007 [US1] Implement `request_confirm` special-case handling in `RoverLoop.tick()` in `server/app/agent.py` — when action is `request_confirm`: call `host.create_confirm()`, build context dict (position, battery, storm), broadcast `confirm_request` event via `make_message`, `await asyncio.wait_for(event.wait(), timeout)`, on timeout broadcast `confirm_timeout` event and treat as denied, on response return confirmed bool, call `host.cleanup_confirm()` after

**Checkpoint**: Rover LLM can call request_confirm. The loop pauses, events are emitted, timeout works.

---

## Phase 4: User Story 2 — Backend Pause & Resume (Priority: P1)

**Goal**: `/api/confirm` REST endpoint accepts human decisions and unblocks the rover.

**Independent Test**: `uv run pytest tests/test_confirm.py -v -k "TestConfirmEndpoint"`

### Tests for User Story 2

- [X] T008 [P] [US2] Add TestConfirmEndpoint class to `server/tests/test_confirm.py` (5 tests: valid confirm returns ok, valid deny returns ok, not-found request_id returns error, missing confirmed field returns error, response broadcasts confirm_response event)

### Implementation for User Story 2

- [X] T009 [US2] Add `POST /api/confirm` endpoint in `server/app/main.py` — accepts `{"request_id": str, "confirmed": bool}`, validates body, calls `host.resolve_confirm()`, broadcasts `confirm_response` event via `make_message(source="human", type="command", name="confirm_response", ...)`, returns `{"ok": true/false, ...}`

**Checkpoint**: Human can respond to confirmations via REST. Response unblocks the rover and broadcasts to all clients.

---

## Phase 5: User Story 3 — Frontend Confirmation Modal (Priority: P2)

**Goal**: Modal overlay appears in the UI when a rover requests confirmation, with Confirm/Deny buttons and a countdown timer.

**Independent Test**: Start simulation, observe modal when rover emits `confirm_request`; click Confirm or Deny; verify modal dismisses and event log updates.

### Implementation for User Story 3

- [X] T010 [P] [US3] Create `ui/src/components/ConfirmModal.vue` — fixed overlay (z-index 400), agent name header, question text, context display (position, battery, storm phase), countdown timer bar (visual + seconds remaining), Confirm (green) and Deny (red) buttons, auto-dismiss on timeout or response, uses CSS variables from App.vue theme
- [X] T011 [US3] Integrate ConfirmModal into `ui/src/pages/SimulationPage.vue` — import component, add `pendingConfirm` ref, route `confirm_request` event in `onSimEvent()` to populate ref, route `confirm_response`/`confirm_timeout` to clear ref, render ConfirmModal with Transition wrapper, implement `handleConfirm(confirmed)` function that POSTs to `/api/confirm`

**Checkpoint**: UI shows confirmation modal with countdown. Human can click Confirm or Deny. Modal auto-dismisses on timeout.

---

## Phase 6: User Story 4 — Rover Prompt Integration (Priority: P3)

**Goal**: Rover system prompt guides the LLM on when to use `request_confirm`.

**Independent Test**: `uv run pytest tests/test_confirm.py -v -k "TestRoverConfirmPrompt"`

### Tests for User Story 4

- [X] T012 [P] [US4] Add TestRoverConfirmPrompt class to `server/tests/test_confirm.py` (4 tests: system prompt contains "HUMAN CONFIRMATION" section, mentions storm zones, mentions hazard tiles, mentions low battery, discourages overuse with "Do NOT" or similar)

### Implementation for User Story 4

- [X] T013 [US4] Add "HUMAN CONFIRMATION" section to the rover system prompt in `_build_context()` in `server/app/agent.py` — placed after storm info section, includes: when to use (entering storm zones, crossing hazard tiles, battery below 15%), when NOT to use (routine moves, safe areas), example question format

**Checkpoint**: Rover LLM has guidance on appropriate use of request_confirm. Tests verify prompt content.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression testing, formatting, documentation.

- [X] T014 Run full test suite — 758 passed, 0 failures
- [X] T015 [P] Run ruff format + ruff check — all clean
- [X] T016 [P] Update `Changelog.md` with human-in-the-loop feature entry
- [X] T017 Run quickstart.md validation steps — 758 passed, ruff clean

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No dependencies — can start immediately. BLOCKS all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 completion (needs Host confirmation methods)
- **Phase 4 (US2)**: Depends on Phase 2 completion (needs Host confirmation methods). Can run in parallel with US1.
- **Phase 5 (US3)**: Depends on Phase 3 + Phase 4 (needs backend events to test against). Frontend-only changes.
- **Phase 6 (US4)**: No dependency on US2/US3, only on Phase 2. Can run in parallel with US1/US2/US3.
- **Phase 7 (Polish)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1) + US2 (P1)**: Both depend on Foundational. Can run in parallel with each other.
- **US3 (P2)**: Depends on US1 + US2 (needs confirm_request events and /api/confirm endpoint)
- **US4 (P3)**: Independent of US2/US3. Only needs Foundational complete.

### Parallel Opportunities

```text
Phase 2:  T001 (tests) || T002+T003 (implementation)
Phase 3+4: US1 (T005-T007) || US2 (T009) — different files (agent.py vs main.py)
Phase 3+6: US1 (T007) → US4 (T013) — same file but independent sections
Phase 5:   T010 (ConfirmModal.vue) || backend work
```

---

## Parallel Example: Agent Swarm

```bash
# After Phase 2 is complete, launch 3 parallel agents:
Agent 1 (backend-tools):   T005, T006, T007 (US1 — agent.py tool + tick)
Agent 2 (backend-api):     T009 (US2 — main.py endpoint)
Agent 3 (frontend):        T010, T011 (US3 — ConfirmModal.vue + SimulationPage.vue)

# After Agent 1 completes:
Agent 4 (prompt):          T013 (US4 — agent.py prompt section)
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 2: Host confirmation infrastructure
2. Complete Phase 3: REQUEST_CONFIRM_TOOL + tick execution
3. Complete Phase 4: /api/confirm endpoint
4. **STOP and VALIDATE**: Test full confirmation flow via tests
5. Backend is functional — can test with curl/httpie

### Incremental Delivery

1. Phase 2 → Foundation ready
2. US1 + US2 → Backend flow complete (MVP)
3. US3 → Frontend modal adds human interaction
4. US4 → Prompt guidance improves LLM behavior
5. Polish → Regression, formatting, changelog
