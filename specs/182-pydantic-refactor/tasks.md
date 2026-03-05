# Tasks: Station Power Allocation Tool (allocate_power) + Budget Events

**Input**: Design documents from `/specs/182-pydantic-refactor/`
**Prerequisites**: plan.md, data-model.md, research.md, contracts/websocket-message-schema.md, quickstart.md

**Tests**: Included — the CLAUDE.md requires complete test coverage before PR.

**Organization**: Tasks grouped by user story derived from feature scope.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project initialization needed. This feature extends an existing codebase. Phase 1 covers WORLD state initialization changes that all stories depend on.

- [X] T001 Add `power_budgets`, `emergency_mode`, and `_power_warn_ticks` fields to WORLD dict initialization in `server/app/world.py`
- [X] T002 Add `STATION_POWER_CAPACITY = 1.0` and `POWER_WARN_COOLDOWN = 3` constants in `server/app/world.py`
- [X] T003 [P] Add `power_budgets: dict[str, float] = {}` and `emergency_mode: bool = False` fields to the `StationContext` Pydantic model in `server/app/models.py`

**Checkpoint**: WORLD state and StationContext have power budget fields. No behavioral changes yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core execution logic that US2 (events) and US3 (routing) depend on.

- [X] T004 Implement `_execute_allocate_power(agent_id: str, amount: float) -> dict` in `server/app/world.py`
- [X] T005 Implement `allocate_power(agent_id: str, amount: float) -> dict` public wrapper in `server/app/world.py`

**Checkpoint**: Foundation ready — allocate_power execution works in isolation.

---

## Phase 3: User Story 1 - allocate_power Tool (Priority: P1)

### Tests for User Story 1

- [X] T006 [P] [US1] Create test file `server/tests/test_power_budget.py` with TestAllocatePower class (9 tests)

### Implementation for User Story 1

- [X] T007 [US1] Define `ALLOCATE_POWER_TOOL` dict in `server/app/station.py`
- [X] T008 [US1] Add `ALLOCATE_POWER_TOOL` to the `STATION_TOOLS` list in `server/app/station.py`
- [X] T009 [US1] Add `allocate_power` case to `execute_action()` and `_parse_tool_calls()` in `server/app/station.py`
- [X] T010 [US1] Verified `allocate_power` handled by generic broadcast in `route_station_actions()` in `server/app/host.py`

**Checkpoint**: Station LLM can call allocate_power. Budget stored in WORLD. Broadcast via WebSocket.

---

## Phase 4: User Story 2 - Budget Warning & Emergency Events (Priority: P2)

### Tests for User Story 2

- [X] T011 [P] [US2] TestPowerBudgetWarning class in `server/tests/test_power_budget.py` (8 tests)
- [X] T012 [P] [US2] TestEmergencyMode class in `server/tests/test_power_budget.py` (6 tests)

### Implementation for User Story 2

- [X] T013 [US2] Implement `check_power_budgets(tick: int) -> list[dict]` in `server/app/world.py`
- [X] T014 [US2] Call `check_power_budgets(tick)` from `next_tick()` in `server/app/world.py`, updated all 3 callers in `agent.py`
- [X] T015 [US2] Broadcast power budget events from rover tick loop in `server/app/agent.py`
- [X] T016 [US2] Add PowerBudgetWarning/EmergencyMode events to station memory via `record_memory()` in `server/app/agent.py`

**Checkpoint**: Budget monitoring active. Warnings and emergency events fire and reach UI + station LLM.

---

## Phase 5: User Story 3 - Station System Prompt & Context (Priority: P3)

### Tests for User Story 3

- [X] T017 [P] [US3] TestPowerManagementContext class in `server/tests/test_station.py` (12 tests)

### Implementation for User Story 3

- [X] T018 [US3] Add "POWER MANAGEMENT" section to the station system prompt in `server/app/station.py`
- [X] T019 [US3] Populate `power_budgets` and `emergency_mode` in StationContext builder (`observe_station()` in `server/app/world.py`) and `_build_world_summary()` in `server/app/station.py`

**Checkpoint**: Station LLM has full power management context and guidance.

---

## Phase 6: User Story 4 - UI Power Budget Indicator (Priority: P4)

### Implementation for User Story 4

- [X] T020 [P] [US4] Create `ui/src/components/PowerBudgetBar.vue` — inline bar with blue fill, "B:" label prefix
- [X] T021 [US4] Update `ui/src/components/AgentPane.vue` and `ui/src/components/AgentPanes.vue` with PowerBudgetBar integration
- [X] T022 [US4] Strip `_power_warn_ticks` from `get_snapshot()` in `server/app/world.py` (power_budgets/emergency_mode already included via deepcopy)

**Checkpoint**: UI shows power budget status for all budgeted agents.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression testing, formatting, documentation.

- [X] T023 Run full test suite — 738 passed, 0 failed
- [X] T024 [P] Run ruff format + ruff check — all clean
- [X] T025 [P] Update `Changelog.md` with power allocation feature entry
- [X] T026 Run quickstart.md validation steps — 738 passed, 0 failed, ruff clean

---
