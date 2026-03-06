# Feature Specification: Upgrade System Tests

**Feature Branch**: `190-upgrade-system-tests`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "Close the validation gap on the base upgrade and building upgrade systems by writing comprehensive tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Base Upgrade Contract Validation (Priority: P1)

As a developer maintaining the Mars simulation, I need comprehensive tests for the base upgrade system so that all 4 upgrade types (charge_mk2, extended_fuel, enhanced_scanner, repair_bay) are validated for correct behavior including prerequisites, resource costs, level tracking, and applied effects.

**Why this priority**: Base upgrades directly affect core agent capabilities (charge rate, fuel capacity, scanner radius, auto-repair). Without comprehensive test coverage, regressions in these systems would silently break gameplay.

**Independent Test**: Can be fully tested by running the test suite against the world module's `_execute_upgrade_base()` function and verifying each upgrade type's contract independently.

**Acceptance Scenarios**:

1. **Given** a rover at the station with sufficient resources, **When** each of the 4 upgrade types is applied, **Then** the upgrade succeeds, level increments, and correct resources are deducted.
2. **Given** a successful charge_mk2 upgrade, **When** a rover charges at the station, **Then** the charge rate is doubled compared to pre-upgrade.
3. **Given** a successful extended_fuel upgrade at level 1, **When** the rover's effective fuel capacity is checked, **Then** it is increased by 100.
4. **Given** a successful enhanced_scanner upgrade at level 1, **When** the rover's reveal radius is checked, **Then** it is increased by 1.
5. **Given** a successful repair_bay upgrade, **When** a rover is at the station during a tick, **Then** the rover's battery is set to full.
6. **Given** a rover not at the station, **When** an upgrade is attempted, **Then** the upgrade fails with a position error.
7. **Given** insufficient water or gas, **When** an upgrade is attempted, **Then** the upgrade fails with a resource error.
8. **Given** an upgrade already at max_level, **When** a further upgrade is attempted, **Then** the upgrade fails with a max level error.
9. **Given** a drone or hauler agent, **When** an upgrade_base action is attempted, **Then** it is rejected.

---

### User Story 2 - Building Upgrade Contract Validation (Priority: P2)

As a developer, I need comprehensive tests for the building upgrade system so that each structure type (refinery, solar_panel_structure, accumulator) is validated for correct bonus calculations at all upgrade levels.

**Why this priority**: Building upgrades use a multiplier formula (1.5^(level-1)) that affects multiple structure attributes differently. Without level-by-level validation, subtle math errors could go undetected.

**Independent Test**: Can be fully tested by running the test suite against `_execute_upgrade_building()` and `_apply_upgrade_bonuses()` with each structure type at each upgrade level.

**Acceptance Scenarios**:

1. **Given** a refinery at level 1, **When** upgraded to level 2, **Then** processing_capacity is multiplied by 1.5.
2. **Given** a refinery at level 2, **When** upgraded to level 3, **Then** processing_capacity is multiplied by 2.25 (from base).
3. **Given** a solar panel at level 1, **When** upgraded to level 2, **Then** charge_rate is multiplied by 1.5 and charge_radius increases by 1.
4. **Given** a solar panel at level 2, **When** upgraded to level 3, **Then** charge_rate is multiplied by 2.25 (from base) and charge_radius increases by 2 (from base).
5. **Given** an accumulator at level 1, **When** upgraded to level 2, **Then** recharge_rate is multiplied by 1.5 and recharge_interval decreases by 1.
6. **Given** an accumulator at level 2, **When** upgraded to level 3, **Then** recharge_interval is clamped at minimum 1.
7. **Given** one structure upgraded, **When** a different structure is inspected, **Then** it remains unchanged.
8. **Given** a drone or hauler agent, **When** an upgrade_building action is attempted, **Then** it is rejected.

---

### User Story 3 - Multi-Level and Integration Validation (Priority: P3)

As a developer, I need integration tests that validate multi-level upgrade progression and end-to-end flows (resources gathered, upgrade applied, effect verified) to ensure the upgrade systems work correctly as part of the broader simulation.

**Why this priority**: Individual unit tests may pass while integration between resource management and upgrade effects could still break. Multi-level tests catch cumulative calculation errors.

**Independent Test**: Can be fully tested by setting up world state with resources, executing upgrades at multiple levels, and verifying cumulative effects.

**Acceptance Scenarios**:

1. **Given** extended_fuel upgraded twice (to level 2), **When** the rover's effective fuel capacity is checked, **Then** it is increased by 200.
2. **Given** enhanced_scanner upgraded twice (to level 2), **When** the rover's reveal radius is checked, **Then** it is increased by 2.
3. **Given** a rover with resources at the station, **When** a base upgrade is performed followed by verifying the effect, **Then** the full flow succeeds.
4. **Given** an active storm, **When** a rover at the station upgrades, **Then** the upgrade still succeeds (storms do not block upgrades).

---

### Edge Cases

- What happens when upgrade_base is called with no `upgrade` parameter (None/missing)?
- What happens when station_resources key does not exist in the world state?
- What happens when a building is upgraded and then re-upgraded (base_contents caching)?
- What happens when multiple structures are adjacent and only the first is targeted?
- What happens when accumulator recharge_interval would go below 1 after multiple upgrades?
- What happens when the return value structure from upgrade actions is missing expected keys?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tests MUST validate all 4 base upgrade types succeed when prerequisites are met (correct position, sufficient resources, below max_level)
- **FR-002**: Tests MUST verify each base upgrade type's specific gameplay effect is correctly applied (charge_mk2 doubles charge rate, extended_fuel adds 100 capacity, enhanced_scanner adds 1 radius, repair_bay enables auto-repair)
- **FR-003**: Tests MUST verify exact resource deduction (water and gas) for each upgrade type matches the UPGRADES configuration
- **FR-004**: Tests MUST verify max_level enforcement per upgrade type (charge_mk2 max 1, extended_fuel max 2, enhanced_scanner max 2, repair_bay max 1)
- **FR-005**: Tests MUST verify failure cases: wrong position, insufficient water only, insufficient gas only, unknown upgrade name, drone/hauler agent types
- **FR-006**: Tests MUST validate building upgrade bonus calculations at each level (1, 2, 3) for each structure type (refinery, solar_panel_structure, accumulator)
- **FR-007**: Tests MUST verify solar panel charge_radius increases by (level - 1) from base
- **FR-008**: Tests MUST verify accumulator recharge_interval is clamped at minimum 1
- **FR-009**: Tests MUST verify upgrading one structure does not affect other structures
- **FR-010**: Tests MUST verify multi-level upgrades produce cumulative effects (e.g., extended_fuel level 2 = +200 capacity)
- **FR-011**: Tests MUST verify return value structure contains expected keys (ok, upgrade/structure_type, new_level, etc.)
- **FR-012**: Tests MUST verify drone and hauler agents cannot use upgrade_building action

### Key Entities

- **Base Upgrade**: One of 4 station upgrade types with water/gas costs, max_level, and gameplay effects; tracked in station_upgrades dict
- **Building Upgrade**: Structure-level upgrade with level 1-3 range, basalt cost, battery cost, and type-specific bonus multipliers
- **Station Resources**: Water and gas reserves used as currency for base upgrades
- **Structure**: In-world building (refinery, solar_panel_structure, accumulator) that can be upgraded with level-specific bonus calculations

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the 4 base upgrade types have at least one success-path test and one failure-path test
- **SC-002**: All 4 base upgrade effect verifications pass (charge rate doubling, fuel capacity increase, scanner radius increase, auto-repair)
- **SC-003**: All 3 building structure types have bonus calculations validated at levels 1, 2, and 3
- **SC-004**: All tests pass when run via `uv run pytest tests/test_upgrade_contract.py -x -q`
- **SC-005**: No production code is modified (tests-only change) unless a genuine bug is discovered
- **SC-006**: Test count in the new file is at least 25 covering the specified scenarios
