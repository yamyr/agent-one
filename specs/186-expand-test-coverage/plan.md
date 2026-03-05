# Plan: Expand Test Coverage

## Phase 1: Core Action Tests
1. [x] Create `server/tests/test_coverage_expansion.py`
2. [x] Implement `TestCollectGas` (8 tests: success, battery deduction, no adjacent plant, empty plant, low battery, inactive plant, drone blocked, hauler blocked)
3. [x] Implement `TestStationRecallAgent` (4 tests: success, default reason, hauler recall, unknown action)
4. [x] Implement `TestUpgradeBaseEdgeCases` (9 tests: wrong position, max level, unknown upgrade, insufficient water, insufficient gas, all types succeed, resource deduction, drone blocked, hauler blocked)

## Phase 2: Agent Loop Tests
5. [x] Implement `TestHaulerLoopTick` (4 tests: tick with action, broadcast thinking+action, goal confidence update, auto-charge at station)

## Phase 3: Integration Tests
6. [x] Implement `TestResourceLifecycle` (3 tests: full dig->drop->pickup->unload chain, dig requires analyzed stone, analyze->dig chain)
7. [x] Implement `TestStormBatteryEffects` (6 tests: clear multiplier, active multiplier, move cost increase, collect_gas cost increase, max intensity, lifecycle phases)

## Phase 4: Finalize
8. [x] Run ruff format and ruff check
9. [x] Run full test suite -- 825 passed, 3 skipped
10. [x] Update Changelog.md
11. [x] Commit changes
