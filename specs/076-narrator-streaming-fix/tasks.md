# Tasks: Non-Blocking Narration Streaming

**Input**: Design documents from `/specs/076-narrator-streaming-fix/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required. Add regression coverage for non-blocking behavior and chunk compatibility.

**Organization**: Tasks grouped by user story to keep each increment independently testable.

## Phase 1: Setup

- [ ] T001 Confirm baseline narrator behavior and capture current failing/perf symptom in `server/tests/test_narrator.py`

---

## Phase 2: Foundational (Blocking)

- [ ] T002 Implement non-blocking stream iteration boundary in `server/app/narrator.py`
- [ ] T003 Preserve existing chunk emission semantics and ordering in `server/app/narrator.py`
- [ ] T004 Add defensive error-path handling for stream interruptions in `server/app/narrator.py`

**Checkpoint**: Narration streaming no longer blocks async loop under normal flow.

---

## Phase 3: User Story 1 - Keep Simulation Responsive During Narration (P1)

**Goal**: Simulation and websocket pipeline remains active while narration streams.

**Independent Test**: Stream narration for several seconds and assert other async activity progresses concurrently.

- [ ] T005 [US1] Add regression test for non-blocking loop progression during streaming in `server/tests/test_narrator.py`
- [ ] T006 [US1] Validate tick/event progression assertions under active stream window in `server/tests/test_narrator.py`

---

## Phase 4: User Story 2 - Preserve Narration Chunk Behavior (P2)

**Goal**: Chunk event structure and ordering remain unchanged.

**Independent Test**: Existing and new chunk tests pass with consistent ordering/content.

- [ ] T007 [US2] Add compatibility assertions for chunk ordering/content in `server/tests/test_narrator.py`
- [ ] T008 [US2] Ensure no schema/name regressions in emitted narration messages via tests in `server/tests/test_narrator.py`

---

## Phase 5: User Story 3 - Handle Streaming Failures Gracefully (P3)

**Goal**: Stream errors do not halt simulation progression.

**Independent Test**: Inject stream failures and verify safe continuation.

- [ ] T009 [US3] Add error-path regression test with partial stream then failure in `server/tests/test_narrator.py`
- [ ] T010 [US3] Verify failure path preserves process stability and emits no malformed events in `server/tests/test_narrator.py`

---

## Phase 6: Polish & Validation

- [ ] T011 Run server formatting checks: `cd server && uv run ruff format --check app/ tests/`
- [ ] T012 Run server lint checks: `cd server && uv run ruff check app/ tests/`
- [ ] T013 Run narrator test suite: `cd server && uv run pytest tests/test_narrator.py -q`
- [ ] T014 Run full server tests: `cd server && uv run pytest tests/ -q`
- [ ] T015 Update `Changelog.md` and issue linkage notes after implementation

## Dependencies & Order

- T002-T004 block all story phases.
- US1 (T005-T006) should be completed before US2/US3 validation signoff.
- US2 (T007-T008) and US3 (T009-T010) can run in parallel after foundational work.
- Final validation (T011-T015) runs after all story tasks are complete.
