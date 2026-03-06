# Tasks: Automatic Request Confirm

**Input**: Design documents from `/specs/190-auto-request-confirm/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: Included — comprehensive test coverage is explicitly required by the spec (SC-008).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Server**: `server/app/` for source, `server/tests/` for tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the config toggle that all user stories depend on

- [x] T001 Add `auto_confirm_enabled: bool = True` setting to Settings class in `server/app/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core hazard detection function and async confirm gate that ALL user stories depend on

- [x] T002 Add `BATTERY_THRESHOLD_AUTO_CONFIRM = 0.15` constant and `detect_move_hazards(agent_id, dest_x, dest_y, move_cost)` function to `server/app/world.py` — returns `list[str]` of hazard descriptions by checking: (1) geyser at destination in "erupting" or "warning" state via `_obstacle_index`, (2) post-move battery < 0.15, (3) storm active with intensity > 0.5 via `storm_mod`
- [x] T003 Add `async _auto_confirm_gate(host, agent_id, action_name, params)` helper function to `server/app/agent.py` — for move actions when `settings.auto_confirm_enabled` is True: compute destination `(tx, ty)` and cost from params (same logic as `execute_action`), call `detect_move_hazards()`, if hazards found create confirm via `host.create_confirm()`, broadcast `confirm_request` event, wait with `CONFIRM_DEFAULT_TIMEOUT`, return `None` if confirmed or `{"ok": False, "error": "..."}` if denied/timed out
- [x] T004 Create test file `server/tests/test_auto_confirm.py` with `TestDetectMoveHazards` class containing foundational tests: test returns empty list when no hazards, test helper imports work correctly

**Checkpoint**: Foundation ready — hazard detection and confirm gate are implemented, user story integration can begin

---

## Phase 3: User Story 1 - Auto-Confirm on Hazardous Move (Priority: P1) MVP

**Goal**: Moves toward geyser tiles in warning/erupting state trigger automatic confirmation

**Independent Test**: Set up world with geyser at destination, issue move, verify hazard is detected and confirmation flow triggers

### Tests for User Story 1

- [x] T005 [P] [US1] Add test `test_geyser_erupting_detected` to `TestDetectMoveHazards` in `server/tests/test_auto_confirm.py` — place erupting geyser at destination, assert detect_move_hazards returns non-empty list with "erupting geyser" description
- [x] T006 [P] [US1] Add test `test_geyser_warning_detected` in `server/tests/test_auto_confirm.py` — place warning-phase geyser at destination, assert hazard detected
- [x] T007 [P] [US1] Add test `test_geyser_idle_no_hazard` in `server/tests/test_auto_confirm.py` — place idle geyser at destination, assert empty list returned
- [x] T008 [P] [US1] Add test `test_no_geyser_no_hazard` in `server/tests/test_auto_confirm.py` — no obstacles at destination, assert empty list

### Implementation for User Story 1

- [x] T009 [US1] Integrate `_auto_confirm_gate()` call before `execute_action()` in the rover agent loop in `server/app/agent.py` (~line 2118) — if gate returns a result dict, use it instead of calling execute_action; if returns None, proceed normally
- [x] T010 [US1] Integrate `_auto_confirm_gate()` call before `execute_action()` in the drone agent loop in `server/app/agent.py` (~line 2473) — same pattern as rover
- [x] T011 [US1] Integrate `_auto_confirm_gate()` call before `execute_action()` in the hauler agent loop in `server/app/agent.py` (~line 2660) — same pattern as rover

**Checkpoint**: Geyser hazard detection is live for all 3 agent types. Moves toward erupting/warning geysers trigger confirmation.

---

## Phase 4: User Story 2 - Auto-Confirm on Low Battery (Priority: P1)

**Goal**: Moves that would drop battery below 15% trigger automatic confirmation

**Independent Test**: Set agent battery to 16%, compute a move cost that brings it below 15%, verify hazard detected

### Tests for User Story 2

- [x] T012 [P] [US2] Add test `test_low_battery_detected` in `server/tests/test_auto_confirm.py` — set agent battery to 0.16, move_cost to 0.02, assert hazard with "battery" in description
- [x] T013 [P] [US2] Add test `test_battery_ok_no_hazard` in `server/tests/test_auto_confirm.py` — set agent battery to 0.50, move_cost to 0.02, assert empty list

### Implementation for User Story 2

- [x] T014 [US2] Verify battery check logic in `detect_move_hazards()` in `server/app/world.py` — confirm `(agent["battery"] - move_cost) < BATTERY_THRESHOLD_AUTO_CONFIRM` check is correct and message includes current and post-move battery percentages

**Checkpoint**: Low battery moves also trigger confirmation. Combined with US1, two of three hazard types are active.

---

## Phase 5: User Story 3 - Auto-Confirm During Active Storm (Priority: P2)

**Goal**: Moves during active storms with intensity > 0.5 trigger confirmation

**Independent Test**: Set storm to active with intensity 0.7, issue move, verify hazard detected

### Tests for User Story 3

- [x] T015 [P] [US3] Add test `test_storm_high_intensity_detected` in `server/tests/test_auto_confirm.py` — set storm phase to "active", intensity to 0.7, assert hazard with "storm" in description
- [x] T016 [P] [US3] Add test `test_storm_low_intensity_no_hazard` in `server/tests/test_auto_confirm.py` — set storm phase to "active", intensity to 0.3, assert empty list
- [x] T017 [P] [US3] Add test `test_storm_clear_no_hazard` in `server/tests/test_auto_confirm.py` — set storm phase to "clear", assert empty list

### Implementation for User Story 3

- [x] T018 [US3] Verify storm check logic in `detect_move_hazards()` in `server/app/world.py` — confirm storm phase == "active" and intensity > 0.5 check is correct and message includes intensity value

**Checkpoint**: All three hazard types (geyser, battery, storm) are active for all agent types.

---

## Phase 6: User Story 4 - Configuration Toggle (Priority: P2)

**Goal**: Auto-confirm can be disabled via `auto_confirm_enabled` setting

**Independent Test**: Set auto_confirm_enabled=False, move toward geyser, verify no confirmation triggered

### Tests for User Story 4

- [x] T019 [P] [US4] Add test `test_config_disabled_skips_hazard_check` in `server/tests/test_auto_confirm.py` — monkeypatch `settings.auto_confirm_enabled = False`, set up geyser at destination, verify `_auto_confirm_gate` returns None (no blocking)
- [x] T020 [P] [US4] Add test `test_config_enabled_default` in `server/tests/test_auto_confirm.py` — verify `settings.auto_confirm_enabled` defaults to True

### Implementation for User Story 4

- [x] T021 [US4] Verify early-return in `_auto_confirm_gate()` in `server/app/agent.py` checks `settings.auto_confirm_enabled` and returns None immediately when disabled

**Checkpoint**: Feature can be toggled off. Safe for demos/testing without human operators.

---

## Phase 7: User Story 5 - Timeout Behavior (Priority: P3)

**Goal**: Unanswered confirmation requests time out and deny the move

**Independent Test**: Create auto-confirm, let timeout elapse, verify move denied

### Tests for User Story 5

- [x] T022 [US5] Add test `test_combined_hazards_single_message` in `server/tests/test_auto_confirm.py` — set erupting geyser + low battery + active storm, assert all three hazards listed in result

### Implementation for User Story 5

- [x] T023 [US5] Verify timeout handling in `_auto_confirm_gate()` in `server/app/agent.py` — confirm `asyncio.wait_for` uses `CONFIRM_DEFAULT_TIMEOUT`, confirm timeout results in `{"ok": False, "error": "...timeout..."}`

**Checkpoint**: Timeout safety net is verified. Full feature is complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, cleanup, and final validation

- [x] T024 [P] Add test `test_non_move_action_not_gated` in `server/tests/test_auto_confirm.py` — verify `_auto_confirm_gate` returns None for action_name != "move" (e.g., "dig", "analyze")
- [x] T025 [P] Add test `test_geyser_not_at_destination_no_hazard` in `server/tests/test_auto_confirm.py` — place geyser at different tile than destination, assert no hazard
- [x] T026 Run `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/` to fix any formatting issues
- [x] T027 Run `cd server && uv run pytest tests/ -x -q` to verify all tests pass
- [x] T028 Update `Changelog.md` with auto-confirm feature changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (config setting) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion (T002, T003, T004)
- **US2 (Phase 4)**: Depends on Phase 2 — can run in parallel with US1
- **US3 (Phase 5)**: Depends on Phase 2 — can run in parallel with US1, US2
- **US4 (Phase 6)**: Depends on Phase 2 — can run in parallel with US1-US3
- **US5 (Phase 7)**: Depends on Phase 2 — can run in parallel with US1-US4
- **Polish (Phase 8)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Independent — geyser detection only
- **US2 (P1)**: Independent — battery detection only
- **US3 (P2)**: Independent — storm detection only
- **US4 (P2)**: Requires `_auto_confirm_gate` from Phase 2 to exist
- **US5 (P3)**: Requires `_auto_confirm_gate` from Phase 2 to exist

### Within Each User Story

- Tests written first (TDD where applicable)
- Verify tests target the correct hazard condition
- Integration tasks (T009-T011) modify `agent.py` — cannot run in parallel with each other

### Parallel Opportunities

- T005, T006, T007, T008 — all US1 tests can run in parallel (different test functions)
- T012, T013 — US2 tests can run in parallel
- T015, T016, T017 — US3 tests can run in parallel
- T019, T020 — US4 tests can run in parallel
- T024, T025 — Polish tests can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (different test functions, same file):
Task T005: "test_geyser_erupting_detected"
Task T006: "test_geyser_warning_detected"
Task T007: "test_geyser_idle_no_hazard"
Task T008: "test_no_geyser_no_hazard"

# Then integrate sequentially (all modify agent.py):
Task T009: Rover loop integration
Task T010: Drone loop integration
Task T011: Hauler loop integration
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T004)
3. Complete Phase 3: User Story 1 (T005-T011)
4. **STOP and VALIDATE**: Test geyser auto-confirm independently
5. Run full test suite to verify no regressions

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. Add US1 (geyser) -> Test -> MVP done
3. Add US2 (battery) -> Test -> Two hazard types
4. Add US3 (storm) -> Test -> All hazard types
5. Add US4 (config toggle) -> Test -> Operational flexibility
6. Add US5 (timeout) -> Test -> Full feature complete
7. Polish -> Ship

---

## Notes

- [P] tasks = different files or test functions, no dependencies
- [Story] label maps task to specific user story for traceability
- T002 and T003 are the core implementation tasks — everything else builds on them
- T009, T010, T011 all modify `agent.py` — do them sequentially
- All hazard detection tests are sync (no async needed)
- Confirm gate tests would need async but are covered by existing test_confirm.py patterns
