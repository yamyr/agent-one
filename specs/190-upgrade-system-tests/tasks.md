# Tasks: Upgrade System Tests

**Input**: Design documents from `/specs/190-upgrade-system-tests/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Organization**: Tasks are grouped by user story. This is a test-only feature -- all tasks create test methods in a single file `server/tests/test_upgrade_contract.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different test classes, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test file with imports, helpers, and base class

- [x] T001 Create `server/tests/test_upgrade_contract.py` with imports (WORLD, execute_action, _execute_upgrade_base, _execute_upgrade_building, _apply_upgrade_bonuses, _effective_fuel_capacity, _reveal_radius_for, _get_upgrade_level, _execute_charge, UPGRADES, UPGRADE_MAX_LEVEL, MAX_UPGRADE_LEVEL, CHARGE_RATE, FUEL_CAPACITY_ROVER, ROVER_REVEAL_RADIUS, BATTERY_COST_UPGRADE, UPGRADE_BASALT_COST, STRUCTURE_TYPES, storm module)
- [x] T002 Implement `_WorldSaveRestore` base class in `server/tests/test_upgrade_contract.py` (save/restore WORLD state: station_upgrades, station_resources, structures, stones, ground_items, delivered_items, storm, rover agent, hauler agent, station agent; clean-slate setUp with rover at [0,0], battery=1.0, station at [0,0])
- [x] T003 Implement `_make_structure()` helper in `server/tests/test_upgrade_contract.py` (create structure dict with type, position, active, upgrade_level, contents from STRUCTURE_TYPES templates)

**Checkpoint**: Test file scaffolding is ready; all subsequent tasks add test methods

---

## Phase 2: User Story 1 - Base Upgrade Contract Validation (Priority: P1)

**Goal**: Validate all 4 base upgrade types for correct behavior including success paths, effect verification, failure cases, and agent type restrictions

**Independent Test**: `cd server && uv run pytest tests/test_upgrade_contract.py::TestBaseUpgradeSuccess -x -q && uv run pytest tests/test_upgrade_contract.py::TestBaseUpgradeEffects -x -q && uv run pytest tests/test_upgrade_contract.py::TestBaseUpgradeFailures -x -q`

### Success Path Tests

- [x] T004 [P] [US1] Write `TestBaseUpgradeSuccess.test_charge_mk2_succeeds` in `server/tests/test_upgrade_contract.py` -- rover at station, water=100, gas=100, upgrade charge_mk2, assert ok=True, new_level=1, cost={water:50, gas:20}
- [x] T005 [P] [US1] Write `TestBaseUpgradeSuccess.test_extended_fuel_succeeds` in `server/tests/test_upgrade_contract.py` -- rover at station, water=100, gas=100, upgrade extended_fuel, assert ok=True, new_level=1, cost={water:30, gas:10}
- [x] T006 [P] [US1] Write `TestBaseUpgradeSuccess.test_enhanced_scanner_succeeds` in `server/tests/test_upgrade_contract.py` -- rover at station, water=100, gas=100, upgrade enhanced_scanner, assert ok=True, new_level=1, cost={water:20, gas:15}
- [x] T007 [P] [US1] Write `TestBaseUpgradeSuccess.test_repair_bay_succeeds` in `server/tests/test_upgrade_contract.py` -- rover at station, water=100, gas=100, upgrade repair_bay, assert ok=True, new_level=1, cost={water:40, gas:30}
- [x] T008 [P] [US1] Write `TestBaseUpgradeSuccess.test_resource_deduction_exact` in `server/tests/test_upgrade_contract.py` -- for each upgrade type, verify station_resources water and gas are deducted by exact amounts from UPGRADES config
- [x] T009 [P] [US1] Write `TestBaseUpgradeSuccess.test_return_value_structure` in `server/tests/test_upgrade_contract.py` -- verify result dict contains keys: ok, upgrade, new_level, cost, description

### Effect Verification Tests

- [x] T010 [P] [US1] Write `TestBaseUpgradeEffects.test_charge_mk2_doubles_charge_rate` in `server/tests/test_upgrade_contract.py` -- set station_upgrades={}, charge rover (record rate), set station_upgrades={"charge_mk2": 1}, charge rover again, assert second charge rate is 2x first via _execute_charge() or CHARGE_RATE comparison
- [x] T011 [P] [US1] Write `TestBaseUpgradeEffects.test_extended_fuel_adds_100_capacity` in `server/tests/test_upgrade_contract.py` -- set station_upgrades={"extended_fuel": 1}, call _effective_fuel_capacity(rover), assert equals FUEL_CAPACITY_ROVER + 100
- [x] T012 [P] [US1] Write `TestBaseUpgradeEffects.test_enhanced_scanner_adds_1_radius` in `server/tests/test_upgrade_contract.py` -- set station_upgrades={"enhanced_scanner": 1}, call _reveal_radius_for(rover), assert equals ROVER_REVEAL_RADIUS + 1
- [x] T013 [P] [US1] Write `TestBaseUpgradeEffects.test_repair_bay_auto_repairs_at_station` in `server/tests/test_upgrade_contract.py` -- set station_upgrades={"repair_bay": 1}, rover at station with battery=0.5, verify auto-repair logic sets battery=1.0

### Failure Case Tests

- [x] T014 [P] [US1] Write `TestBaseUpgradeFailures.test_wrong_position` in `server/tests/test_upgrade_contract.py` -- rover at [5,5], station at [0,0], attempt upgrade, assert ok=False, error contains position message
- [x] T015 [P] [US1] Write `TestBaseUpgradeFailures.test_insufficient_water_only` in `server/tests/test_upgrade_contract.py` -- rover at station, water=0, gas=100, attempt charge_mk2, assert ok=False, error mentions water
- [x] T016 [P] [US1] Write `TestBaseUpgradeFailures.test_insufficient_gas_only` in `server/tests/test_upgrade_contract.py` -- rover at station, water=100, gas=0, attempt charge_mk2, assert ok=False, error mentions gas
- [x] T017 [P] [US1] Write `TestBaseUpgradeFailures.test_unknown_upgrade_name` in `server/tests/test_upgrade_contract.py` -- rover at station, attempt upgrade "nonexistent", assert ok=False, error mentions unknown
- [x] T018 [P] [US1] Write `TestBaseUpgradeFailures.test_max_level_charge_mk2` in `server/tests/test_upgrade_contract.py` -- station_upgrades={"charge_mk2": 1}, attempt upgrade charge_mk2 again, assert ok=False, error mentions max level
- [x] T019 [P] [US1] Write `TestBaseUpgradeFailures.test_max_level_extended_fuel` in `server/tests/test_upgrade_contract.py` -- station_upgrades={"extended_fuel": 2}, attempt upgrade extended_fuel again, assert ok=False
- [x] T020 [P] [US1] Write `TestBaseUpgradeFailures.test_max_level_enhanced_scanner` in `server/tests/test_upgrade_contract.py` -- station_upgrades={"enhanced_scanner": 2}, attempt upgrade enhanced_scanner again, assert ok=False
- [x] T021 [P] [US1] Write `TestBaseUpgradeFailures.test_max_level_repair_bay` in `server/tests/test_upgrade_contract.py` -- station_upgrades={"repair_bay": 1}, attempt upgrade repair_bay again, assert ok=False
- [x] T022 [P] [US1] Write `TestBaseUpgradeFailures.test_drone_cannot_upgrade_base` in `server/tests/test_upgrade_contract.py` -- execute_action("drone-mistral", "upgrade_base", {...}), assert ok=False, error mentions drone
- [x] T023 [P] [US1] Write `TestBaseUpgradeFailures.test_hauler_cannot_upgrade_base` in `server/tests/test_upgrade_contract.py` -- execute_action("hauler-mistral", "upgrade_base", {...}), assert ok=False, error mentions hauler
- [x] T024 [P] [US1] Write `TestBaseUpgradeFailures.test_missing_upgrade_param` in `server/tests/test_upgrade_contract.py` -- rover at station, attempt upgrade_base with no upgrade param (None), assert ok=False

**Checkpoint**: All base upgrade contract tests pass independently via `uv run pytest tests/test_upgrade_contract.py -k "TestBaseUpgrade" -x -q`

---

## Phase 3: User Story 2 - Building Upgrade Contract Validation (Priority: P2)

**Goal**: Validate building upgrade bonus calculations at all levels for each structure type (refinery, solar_panel_structure, accumulator)

**Independent Test**: `cd server && uv run pytest tests/test_upgrade_contract.py::TestBuildingUpgradeBonuses -x -q && uv run pytest tests/test_upgrade_contract.py::TestBuildingUpgradeFailures -x -q`

### Bonus Calculation Tests

- [x] T025 [P] [US2] Write `TestBuildingUpgradeBonuses.test_refinery_level2_bonus` in `server/tests/test_upgrade_contract.py` -- create refinery structure, set upgrade_level=2, call _apply_upgrade_bonuses(), assert processing_capacity == int(round(50 * 1.5))
- [x] T026 [P] [US2] Write `TestBuildingUpgradeBonuses.test_refinery_level3_bonus` in `server/tests/test_upgrade_contract.py` -- create refinery, set upgrade_level=3, call _apply_upgrade_bonuses(), assert processing_capacity == int(round(50 * 2.25))
- [x] T027 [P] [US2] Write `TestBuildingUpgradeBonuses.test_solar_panel_level2_bonus` in `server/tests/test_upgrade_contract.py` -- create solar_panel_structure, set upgrade_level=2, call _apply_upgrade_bonuses(), assert charge_rate == round(0.01 * 1.5, 5) and charge_radius == 2
- [x] T028 [P] [US2] Write `TestBuildingUpgradeBonuses.test_solar_panel_level3_bonus` in `server/tests/test_upgrade_contract.py` -- create solar_panel_structure, set upgrade_level=3, call _apply_upgrade_bonuses(), assert charge_rate == round(0.01 * 2.25, 5) and charge_radius == 3
- [x] T029 [P] [US2] Write `TestBuildingUpgradeBonuses.test_accumulator_level2_bonus` in `server/tests/test_upgrade_contract.py` -- create accumulator, set upgrade_level=2, call _apply_upgrade_bonuses(), assert recharge_rate == round(0.01 * 1.5, 5) and recharge_interval == 4
- [x] T030 [P] [US2] Write `TestBuildingUpgradeBonuses.test_accumulator_level3_bonus` in `server/tests/test_upgrade_contract.py` -- create accumulator, set upgrade_level=3, call _apply_upgrade_bonuses(), assert recharge_rate == round(0.01 * 2.25, 5) and recharge_interval == max(1, 5-2) == 3
- [x] T031 [P] [US2] Write `TestBuildingUpgradeBonuses.test_accumulator_interval_clamp_at_1` in `server/tests/test_upgrade_contract.py` -- create accumulator with base recharge_interval=1, set upgrade_level=3, call _apply_upgrade_bonuses(), assert recharge_interval == max(1, 1-2) == 1
- [x] T032 [P] [US2] Write `TestBuildingUpgradeBonuses.test_upgrade_one_structure_does_not_affect_other` in `server/tests/test_upgrade_contract.py` -- create two structures (refinery + solar panel), upgrade only refinery via execute_action, verify solar panel contents unchanged

### Building Upgrade Failure Tests

- [x] T033 [P] [US2] Write `TestBuildingUpgradeFailures.test_drone_cannot_upgrade_building` in `server/tests/test_upgrade_contract.py` -- execute_action("drone-mistral", "upgrade_building", {}), assert ok=False
- [x] T034 [P] [US2] Write `TestBuildingUpgradeFailures.test_hauler_cannot_upgrade_building` in `server/tests/test_upgrade_contract.py` -- execute_action("hauler-mistral", "upgrade_building", {}), assert ok=False
- [x] T035 [P] [US2] Write `TestBuildingUpgradeFailures.test_building_upgrade_return_value_structure` in `server/tests/test_upgrade_contract.py` -- successful building upgrade, verify result contains keys: ok, structure_type, new_level, position

**Checkpoint**: All building upgrade contract tests pass via `uv run pytest tests/test_upgrade_contract.py -k "TestBuildingUpgrade" -x -q`

---

## Phase 4: User Story 3 - Multi-Level and Integration Validation (Priority: P3)

**Goal**: Validate multi-level upgrade progression and end-to-end integration flows

**Independent Test**: `cd server && uv run pytest tests/test_upgrade_contract.py::TestMultiLevelUpgrades -x -q && uv run pytest tests/test_upgrade_contract.py::TestUpgradeIntegration -x -q`

### Multi-Level Tests

- [x] T036 [P] [US3] Write `TestMultiLevelUpgrades.test_extended_fuel_level2_adds_200` in `server/tests/test_upgrade_contract.py` -- upgrade extended_fuel twice (level 1 then level 2), verify _effective_fuel_capacity(rover) == FUEL_CAPACITY_ROVER + 200
- [x] T037 [P] [US3] Write `TestMultiLevelUpgrades.test_enhanced_scanner_level2_adds_2_radius` in `server/tests/test_upgrade_contract.py` -- upgrade enhanced_scanner twice, verify _reveal_radius_for(rover) == ROVER_REVEAL_RADIUS + 2
- [x] T038 [P] [US3] Write `TestMultiLevelUpgrades.test_building_re_upgrade_uses_base_contents` in `server/tests/test_upgrade_contract.py` -- upgrade building to level 2, then level 3, verify _base_contents is preserved and bonuses are calculated from original base values

### Integration Tests

- [x] T039 [P] [US3] Write `TestUpgradeIntegration.test_full_base_upgrade_flow` in `server/tests/test_upgrade_contract.py` -- set up station_resources with water+gas, execute upgrade_base via execute_action, verify resources deducted and effect applied
- [x] T040 [P] [US3] Write `TestUpgradeIntegration.test_upgrade_during_storm` in `server/tests/test_upgrade_contract.py` -- set storm state to active, rover at station, attempt base upgrade, assert still succeeds (storms do not block upgrades)

**Checkpoint**: All multi-level and integration tests pass via `uv run pytest tests/test_upgrade_contract.py -k "TestMultiLevel or TestUpgradeIntegration" -x -q`

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, formatting, and documentation

- [x] T041 Run `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/` to format and lint
- [x] T042 Run full test suite `cd server && uv run pytest tests/ -x -q` to verify no regressions
- [x] T043 Verify test count in test_upgrade_contract.py is at least 25 methods
- [x] T044 Update Changelog.md with upgrade system tests changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- create file, imports, helpers
- **US1 (Phase 2)**: Depends on Setup (Phase 1) completion
- **US2 (Phase 3)**: Depends on Setup (Phase 1) completion -- independent of US1
- **US3 (Phase 4)**: Depends on Setup (Phase 1) completion -- some tests reference upgrade effects tested in US1
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 1 -- No dependencies on other stories
- **User Story 2 (P2)**: Can start after Phase 1 -- Independent of US1 (different test classes, different code paths)
- **User Story 3 (P3)**: Can start after Phase 1 -- Uses same helper functions tested in US1 but tests are self-contained

### Within Each User Story

- All test methods within a class are marked [P] (parallelizable) since they operate on independent world state via setUp/tearDown
- Test classes within a story are independent (different setUp concerns)

### Parallel Opportunities

- T004-T024 (all US1 tests) can be written in parallel since each is an independent test method
- T025-T035 (all US2 tests) can be written in parallel
- T036-T040 (all US3 tests) can be written in parallel
- US1 and US2 phases can proceed in parallel (no cross-dependencies)

---

## Parallel Example: User Story 1

```bash
# All these test methods can be written in parallel (same file, different methods):
T004: TestBaseUpgradeSuccess.test_charge_mk2_succeeds
T005: TestBaseUpgradeSuccess.test_extended_fuel_succeeds
T010: TestBaseUpgradeEffects.test_charge_mk2_doubles_charge_rate
T011: TestBaseUpgradeEffects.test_extended_fuel_adds_100_capacity
T014: TestBaseUpgradeFailures.test_wrong_position
T022: TestBaseUpgradeFailures.test_drone_cannot_upgrade_base
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: User Story 1 -- Base Upgrade Contract Tests (T004-T024)
3. **STOP and VALIDATE**: `cd server && uv run pytest tests/test_upgrade_contract.py -k "TestBaseUpgrade" -x -q`
4. This alone closes the biggest validation gap (effect verification)

### Incremental Delivery

1. Setup (Phase 1) -- file scaffolding ready
2. Add US1 tests (Phase 2) -- base upgrade contracts validated
3. Add US2 tests (Phase 3) -- building upgrade contracts validated
4. Add US3 tests (Phase 4) -- multi-level and integration validated
5. Polish (Phase 5) -- formatting, full suite verification, changelog

---

## Notes

- All tasks create test methods in a single file: `server/tests/test_upgrade_contract.py`
- No production code changes unless a genuine bug is discovered during testing
- Tests use `_WorldSaveRestore` pattern for state isolation (from research.md R1)
- Test effects via helper functions, not just action routing (from research.md R2)
- Test bonuses directly via `_apply_upgrade_bonuses()` for precision (from research.md R3)
- Avoid duplicating tests already in test_upgrades.py and test_coverage_expansion.py (from research.md R4)
