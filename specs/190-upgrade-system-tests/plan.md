# Implementation Plan: Upgrade System Tests

**Branch**: `190-upgrade-system-tests` | **Date**: 2026-03-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/190-upgrade-system-tests/spec.md`

## Summary

Close the validation gap on the base upgrade and building upgrade systems by writing comprehensive tests. Create `server/tests/test_upgrade_contract.py` with 25+ tests covering all 4 base upgrade types (charge_mk2, extended_fuel, enhanced_scanner, repair_bay), all 3 building structure types (refinery, solar_panel_structure, accumulator) with level-by-level bonus validation, multi-level progression, and integration flows. Tests exercise `_execute_upgrade_base()`, `_execute_upgrade_building()`, `_apply_upgrade_bonuses()` and the `execute_action()` routing layer.

## Technical Context

**Language/Version**: Python 3.14+
**Primary Dependencies**: FastAPI (app), unittest (tests), app.world module
**Storage**: In-memory WORLD dict (no database needed for these tests)
**Testing**: pytest with unittest.TestCase classes; direct world state manipulation
**Target Platform**: Server-side (macOS/Linux)
**Project Type**: Web service (test suite addition)
**Performance Goals**: N/A (unit/contract tests)
**Constraints**: Tests only -- no production code changes unless a genuine bug is discovered
**Scale/Scope**: Single new test file, 25+ test methods

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file contains only placeholder template content (no project-specific principles ratified). No gates to evaluate. Proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/190-upgrade-system-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
server/
├── app/
│   └── world.py           # Production code (read-only for this feature)
└── tests/
    ├── test_upgrades.py              # Existing building upgrade tests
    ├── test_coverage_expansion.py    # Existing base upgrade edge case tests
    ├── test_resources.py             # Existing base upgrade basic test
    └── test_upgrade_contract.py      # NEW: comprehensive upgrade contract tests
```

**Structure Decision**: Single new test file `server/tests/test_upgrade_contract.py` following existing test conventions. Uses `_WorldSaveRestore` pattern from `test_coverage_expansion.py` for world state isolation.

## Complexity Tracking

No constitution violations to justify.
