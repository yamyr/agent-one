# Tasks: Multi-Scenario Presets

**Input**: Design documents from `/specs/188-multi-scenario-presets/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included (feature requires validation of preset definitions, application logic, and API endpoints).

**Organization**: Tasks grouped by user story (US1: Definitions, US2: API, US3: Config).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: User Story 1 -- Preset Definitions and Application Logic (Priority: P1)

**Goal**: PRESETS dict and apply_preset() function in server/app/presets.py

**Independent Test**: `cd server && uv run pytest tests/test_presets.py -v -k "preset_def or apply"`

### Tests for User Story 1

- [ ] T001 [P] [US1] Write test `test_presets_dict_has_required_keys` -- verify all 5 presets exist with name, description, world_overrides, agent_overrides fields, in `server/tests/test_presets.py`
- [ ] T002 [P] [US1] Write test `test_default_preset_no_changes` -- apply default preset, verify WORLD unchanged from fresh reset, in `server/tests/test_presets.py`
- [ ] T003 [P] [US1] Write test `test_storm_survival_modifies_world` -- apply storm_survival, verify storm and battery changes, in `server/tests/test_presets.py`
- [ ] T004 [P] [US1] Write test `test_apply_unknown_preset_raises` -- apply non-existent preset raises ValueError, in `server/tests/test_presets.py`

### Implementation for User Story 1

- [ ] T005 [US1] Create `server/app/presets.py` with PRESETS dict (5 presets) and `apply_preset()` function

**Checkpoint**: Presets defined and application logic works; tests pass

---

## Phase 2: User Story 2 -- API Endpoints (Priority: P1)

**Goal**: REST endpoints for listing and applying presets

**Independent Test**: `cd server && uv run pytest tests/test_presets.py -v -k "api"`

### Tests for User Story 2

- [ ] T006 [P] [US2] Write test `test_api_list_presets` -- GET /api/presets returns all presets with name and description, in `server/tests/test_presets.py`
- [ ] T007 [P] [US2] Write test `test_api_apply_preset_success` -- POST /api/presets/storm_survival/apply returns ok, in `server/tests/test_presets.py`
- [ ] T008 [P] [US2] Write test `test_api_apply_unknown_preset_404` -- POST /api/presets/nonexistent/apply returns 404, in `server/tests/test_presets.py`

### Implementation for User Story 2

- [ ] T009 [US2] Add `GET /api/presets` and `POST /api/presets/{name}/apply` endpoints to `server/app/main.py`

**Checkpoint**: API endpoints work correctly; tests pass

---

## Phase 3: User Story 3 -- Config Integration (Priority: P2)

**Goal**: `preset` config field for startup preset

**Independent Test**: `cd server && uv run pytest tests/test_presets.py -v -k "config"`

### Tests for User Story 3

- [ ] T010 [P] [US3] Write test `test_config_preset_field_exists` -- verify Settings has preset field with default "default", in `server/tests/test_presets.py`

### Implementation for User Story 3

- [ ] T011 [US3] Add `preset: str = "default"` to Settings in `server/app/config.py`
- [ ] T012 [US3] Add startup preset application in `lifespan()` in `server/app/main.py`

**Checkpoint**: Setting PRESET env var applies preset on startup; test passes

---

## Phase 4: Polish & Cross-Cutting Concerns

- [ ] T013 Run full test suite: `cd server && uv run pytest tests/ -v`
- [ ] T014 Run ruff format and lint: `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/`
- [ ] T015 Update `Changelog.md` with feature entries
- [ ] T016 Commit all changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (US1)**: No dependencies -- core preset definitions
- **Phase 2 (US2)**: Depends on Phase 1 (apply_preset function)
- **Phase 3 (US3)**: Depends on Phase 1 (apply_preset function)
- **Phase 4 (Polish)**: Depends on all user stories complete

### Execution Order

1. T005: Create presets.py (definitions + apply_preset)
2. T001-T004, T006-T008, T010: Write all tests
3. T009: API endpoints
4. T011-T012: Config integration
5. T013-T016: Polish
