# Research: Upgrade System Tests

## R1: Test Pattern for World State Isolation

**Decision**: Use `_WorldSaveRestore` base class pattern from `test_coverage_expansion.py`
**Rationale**: This pattern saves/restores all relevant WORLD state keys (station_upgrades, station_resources, structures, stones, agents) in setUp/tearDown. It provides clean-slate isolation without requiring database access. Already proven in 15+ tests.
**Alternatives considered**:
- `CaseWithDB` base class from conftest: Requires SurrealDB; overkill for in-memory world state tests
- Direct copy of setUp/tearDown from `test_upgrades.py`: Less comprehensive state restoration (misses station_upgrades, station_resources)
- Fresh `_build_initial_world()` per test: Would require module-level patching of WORLD global; fragile

## R2: How to Test Base Upgrade Effects

**Decision**: Test each upgrade effect by calling the relevant helper function or action after setting station_upgrades:
- `charge_mk2`: Call `_execute_charge()` or `execute_action("rover-mistral", "charge", {})` and compare charge rate with/without upgrade
- `extended_fuel`: Call `_effective_fuel_capacity(agent)` and verify +100 per level
- `enhanced_scanner`: Call `_reveal_radius_for(agent)` and verify +1 per level
- `repair_bay`: Set up world state mimicking station tick logic (rover at station, repair_bay > 0) and verify battery = 1.0

**Rationale**: Testing via the actual helper functions validates the real code paths. The effect functions read from `WORLD["station_upgrades"]` which we control directly.
**Alternatives considered**:
- Mocking `_get_upgrade_level()`: Would bypass the actual integration; less valuable
- Testing only via `execute_action()`: Some effects (fuel capacity, reveal radius) are checked via helper functions, not actions

## R3: How to Test Building Upgrade Bonuses Precisely

**Decision**: Test `_apply_upgrade_bonuses()` directly with structure dicts at each level, then verify exact computed values using known formulas:
- Level 1: multiplier = 1.0 (1.5^0)
- Level 2: multiplier = 1.5 (1.5^1)
- Level 3: multiplier = 2.25 (1.5^2)

**Rationale**: Direct function testing gives precise control over inputs and expected outputs. The multiplier formula is deterministic.
**Alternatives considered**:
- Testing only via `_execute_upgrade_building()`: Couples bonus validation with upgrade action prerequisites; harder to isolate math errors

## R4: Existing Test Coverage Overlap Analysis

**Decision**: The new test file will NOT duplicate tests already in `test_upgrades.py` and `test_coverage_expansion.py`. It will add:
- Effect verification tests (charge_mk2 effect, extended_fuel effect, etc.) -- NOT covered anywhere
- Per-type max_level enforcement -- partially covered (only charge_mk2 in test_coverage_expansion)
- Multi-level progression tests -- NOT covered
- Building upgrade per-structure-type bonus validation at all levels -- NOT covered (only solar_panel at level 2)
- Accumulator and refinery bonus tests -- NOT covered
- Integration flow tests -- NOT covered
- Return value structure validation -- NOT covered

**Rationale**: Avoids bloat while closing the actual validation gap.
**Alternatives considered**:
- Merge into existing test files: Would make them too large; separate contract test file is cleaner

## R5: Imports Required

**Decision**: Import from `app.world`:
- `WORLD` (global state dict)
- `execute_action` (action routing)
- `_execute_upgrade_base`, `_execute_upgrade_building`, `_apply_upgrade_bonuses` (direct function testing)
- `_effective_fuel_capacity`, `_reveal_radius_for`, `_get_upgrade_level` (effect verification)
- `_execute_charge` (charge_mk2 effect verification)
- `UPGRADES`, `UPGRADE_MAX_LEVEL`, `MAX_UPGRADE_LEVEL` (constants)
- `CHARGE_RATE`, `FUEL_CAPACITY_ROVER`, `ROVER_REVEAL_RADIUS` (baseline values)
- `BATTERY_COST_UPGRADE`, `UPGRADE_BASALT_COST` (cost constants)
- `STRUCTURE_TYPES` (for structure template creation)
- `storm` module import via `app.world` for storm state

**Rationale**: Direct imports allow precise testing without going through action routing for unit-level tests.
