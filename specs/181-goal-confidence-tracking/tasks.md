# Tasks: Goal Confidence Tracking + UI Bars

**Input**: Design documents from `/specs/181-goal-confidence-tracking/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/websocket-schema.md

**Tests**: Included — plan.md specifies `test_goal_confidence.py` and CLAUDE.md requires complete test coverage.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: No project initialization needed — existing codebase. This phase is intentionally empty.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add `goal_confidence` field to all shared models and agent initialization. MUST complete before ANY user story.

- [x] T001 [P] Add `goal_confidence: float = 0.5` field to `RoverAgentState` model in `server/app/models.py`
- [x] T002 [P] Add `goal_confidence: float = 0.5` field to `HaulerAgentState` model in `server/app/models.py`
- [x] T003 [P] Add `goal_confidence: float = 0.5` field to `RoverSummary` model in `server/app/models.py`
- [x] T004 Add `"goal_confidence": 0.5` to agent state dicts in `_make_rover()`, `_make_hauler()`, `_make_drone()`, and station init in `server/app/world.py`

**Checkpoint**: All agent types have `goal_confidence` initialized at 0.5. Field is present in Pydantic models. Snapshot automatically includes it via `get_snapshot()` deep copy.

---

## Phase 3: User Story 1 — Confidence Reflects Agent Progress (Priority: P1) MVP

**Goal**: Goal confidence updates dynamically based on action outcomes (success +0.05, failure -0.05, fallback -0.08, hazard -0.08, delivery +0.10). Clamped to [0.0, 1.0]. Resets to 0.5 on mission reassignment.

**Independent Test**: Run `uv run pytest tests/test_goal_confidence.py -v` — all update rules verified without UI or LLM.

### Tests for User Story 1

- [x] T005 [P] [US1] Create test file `server/tests/test_goal_confidence.py` with tests: confidence increases on action success (+0.05), decreases on failure (-0.05), decreases on fallback (-0.08), decreases on hazard (-0.08), increases on delivery (+0.10), clamps to [0.0, 1.0] at boundaries, resets to 0.5 on mission reassignment

### Implementation for User Story 1

- [x] T006 [US1] Add `update_goal_confidence(agent_id: str, delta: float)` helper function in `server/app/world.py` that reads `WORLD["agents"][agent_id]["goal_confidence"]`, applies delta, clamps to [0.0, 1.0], and writes back
- [x] T007 [US1] Add confidence update calls in `RoverLoop.tick()` in `server/app/agent.py`: after `execute_action()` result, call `update_goal_confidence` with +0.05 on success, -0.05 on failure; apply +0.10 bonus for delivery actions (when action_name is "deliver" and action_ok); apply -0.08 on fallback (`is_fallback=True`)
- [x] T008 [US1] Add confidence update for storm/hazard events in `RoverLoop.tick()` in `server/app/agent.py`: when storm events are detected (from `check_storm_tick()`), call `update_goal_confidence` with -0.08
- [x] T009 [US1] Add confidence reset to 0.5 on mission reassignment: in `server/app/world.py`, wherever `agent["mission"]` is reassigned, also set `agent["goal_confidence"] = 0.5`
- [x] T010 [US1] Run tests: `cd server && uv run pytest tests/test_goal_confidence.py -v` — verify all pass

**Checkpoint**: Confidence values update correctly in the world model. Verifiable by inspecting `WORLD["agents"][id]["goal_confidence"]` after actions.

---

## Phase 4: User Story 2 — Confidence Visible in UI (Priority: P2)

**Goal**: Color-coded, animated confidence bar displayed for each agent in the dashboard. Green (0.7–1.0), amber (0.4–0.69), red (0.0–0.39).

**Independent Test**: Open `http://localhost:4089`, run simulation, observe confidence bars updating alongside battery bars in each AgentPane.

### Implementation for User Story 2

- [x] T011 [P] [US2] Create `ui/src/components/ConfidenceBar.vue` — clone `BatteryBar.vue` pattern: props `level` (0–1 float), computed `pct` and `barColor` with thresholds green >=70, amber >=40, red <40 using CSS vars `--accent-green`, `--accent-amber`, `--accent-red`; smooth CSS transition on fill width
- [x] T012 [P] [US2] Add `goalConfidence(id)` helper function in `ui/src/components/AgentPanes.vue` that reads `props.worldState.agents[id]?.goal_confidence ?? 0`; pass `:goal-confidence="goalConfidence(id)"` to each `<AgentPane>` in the template
- [x] T013 [US2] Add `goalConfidence` prop (Number, default 0) to `ui/src/components/AgentPane.vue`; import `ConfidenceBar`; render `<ConfidenceBar :level="goalConfidence" />` alongside existing `<BatteryBar>` in the agent-row-2 section; hide bar when no mission assigned

**Checkpoint**: Dashboard shows animated confidence bars per agent. Colors match spec thresholds.

---

## Phase 5: User Story 3 — LLM Agents Reason About Confidence (Priority: P3)

**Goal**: `goal_confidence` included in observation context passed to LLM reasoning step for all agent types.

**Independent Test**: Add a debug log or breakpoint in `observe_rover()` / `observe_hauler()` — verify `goal_confidence` is present in the returned context object.

### Implementation for User Story 3

- [x] T014 [P] [US3] Pass `goal_confidence=agent.get("goal_confidence", 0.5)` when constructing `RoverAgentState` in `observe_rover()` in `server/app/world.py`
- [x] T015 [P] [US3] Pass `goal_confidence=agent.get("goal_confidence", 0.5)` when constructing `HaulerAgentState` in `observe_hauler()` in `server/app/world.py`
- [x] T016 [US3] Pass `goal_confidence=agent.get("goal_confidence", 0.5)` when constructing `RoverSummary` in `observe_station()` in `server/app/world.py`

**Checkpoint**: LLM context for each agent type includes `goal_confidence`. Station sees confidence of all non-station agents via RoverSummary.

---

## Phase 6: User Story 4 — Confidence in Training Data (Priority: P4)

**Goal**: Training data records include goal_confidence snapshot and before/after deltas per turn.

**Independent Test**: Run simulation, inspect training log output — verify `goal_confidence`, `goal_confidence_before`, `goal_confidence_after` fields present.

### Implementation for User Story 4

- [x] T017 [P] [US4] Add `goal_confidence: float = 0.5` field to `TurnWorldSnapshot` in `server/app/training_models.py`
- [x] T018 [P] [US4] Add `goal_confidence_before: float = 0.5` and `goal_confidence_after: float = 0.5` fields to `TrainingTurn` in `server/app/training_models.py`
- [x] T019 [US4] Populate `goal_confidence` in `_build_turn_snapshot()` in `server/app/agent.py` from `agent_state.get("goal_confidence", 0.5)`
- [x] T020 [US4] Populate `goal_confidence_before` from `pre_rover.get("goal_confidence", 0.5)` and `goal_confidence_after` from `post_rover.get("goal_confidence", 0.5)` in the `TrainingTurn` constructor in `RoverLoop.tick()` in `server/app/agent.py`

**Checkpoint**: Training log entries contain confidence data for every turn.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, formatting, and final quality checks.

- [x] T021 Run full test suite: `cd server && uv run pytest tests/ -v` — verify no regressions
- [x] T022 Run formatter and linter: `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/`
- [x] T023 Run quickstart.md validation: start server + UI, verify confidence bars visible and updating in live simulation
- [x] T024 Update `Changelog.md` with goal confidence tracking feature entry

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Empty — project already exists
- **Foundational (Phase 2)**: No dependencies — can start immediately. BLOCKS all user stories.
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 2 completion (reads goal_confidence from snapshot)
- **US3 (Phase 5)**: Depends on Phase 2 completion (reads goal_confidence from agent state)
- **US4 (Phase 6)**: Depends on Phase 2 completion (reads goal_confidence from agent state)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependencies on other stories
- **US2 (P2)**: After Phase 2 — no dependencies on other stories (displays whatever value is in snapshot)
- **US3 (P3)**: After Phase 2 — no dependencies on other stories (reads whatever value is in agent state)
- **US4 (P4)**: After Phase 2 — no dependencies on other stories (captures whatever value is in agent state)

All four user stories are **independently implementable** after Phase 2. They read the same `goal_confidence` field but don't depend on each other.

### Within Each User Story

- Tests written first (US1 only — other stories don't have dedicated test files)
- Models/fields before logic that uses them
- Core implementation before integration wiring

### Parallel Opportunities

- T001, T002, T003 can run in parallel (different model classes, same file — but simple field additions)
- T011, T012 can run in parallel (different Vue files)
- T014, T015 can run in parallel (different functions in same file)
- T017, T018 can run in parallel (different model classes in same file)
- **US1, US2, US3, US4 can all start in parallel** after Phase 2

---

## Parallel Example: After Phase 2

```bash
# All four stories can launch simultaneously:
# Agent A: US1 — confidence update logic (T005-T010)
# Agent B: US2 — UI confidence bar (T011-T013)
# Agent C: US3 — LLM observation context (T014-T016)
# Agent D: US4 — training data fields (T017-T020)
```

## Parallel Example: Within User Story 2

```bash
# These two can run simultaneously (different files):
Task T011: "Create ConfidenceBar.vue in ui/src/components/ConfidenceBar.vue"
Task T012: "Add goalConfidence helper in ui/src/components/AgentPanes.vue"
# Then T013 depends on both (wires them together in AgentPane.vue)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T004)
2. Complete Phase 3: User Story 1 (T005-T010)
3. **STOP and VALIDATE**: Run `uv run pytest tests/test_goal_confidence.py -v`
4. Confidence values now update correctly in-memory — invisible to UI but working

### Incremental Delivery

1. Phase 2 → Foundation (goal_confidence exists in all agents)
2. + US1 → Confidence updates dynamically (MVP)
3. + US2 → Visible in dashboard (demo-ready)
4. + US3 → LLM agents can introspect on confidence (reasoning loop complete)
5. + US4 → Training data enriched (research-ready)
6. Phase 7 → Polish, tests, changelog

### Recommended Order (Single Developer)

Phase 2 → US1 → US2 → US3 → US4 → Phase 7

This order delivers maximum incremental value: first make it work (US1), then make it visible (US2), then make it intelligent (US3), then make it analyzable (US4).

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable after Phase 2
- Commit after each phase checkpoint
- Total: 24 tasks across 7 phases
