# Research: Test Coverage Gaps

## Analysis Method

Compared existing test files against source code to identify untested functions.

## Findings

### 1. `_execute_collect_gas()` (world.py:2604)
- **Status**: ZERO tests
- **Logic**: Checks battery, finds adjacent gas_plant structure, verifies gas_stored > 0, deducts battery, appends gas to inventory
- **Dependencies**: `storm_mod.get_battery_multiplier`, WORLD structures list
- **Risk**: Medium -- gas collection is a core game mechanic

### 2. `HaulerLoop.tick()` (agent.py:2620)
- **Status**: No tick integration tests
- **Logic**: Drains inbox, calls reasoner, executes action, broadcasts events, updates goal confidence, auto-charges at station
- **Dependencies**: Async, requires mock Host and Broadcaster
- **Risk**: High -- main loop for hauler agent

### 3. Station `recall_agent` (station.py:245)
- **Status**: No direct tests
- **Logic**: Simply returns `{ok: True, agent_id, reason}` -- it's a pass-through command
- **Risk**: Low -- simple logic but good to have coverage

### 4. Resource Lifecycle
- **Status**: Individual actions tested, but no end-to-end chain test
- **Chain**: `dig` -> `drop_item` -> `pickup_cargo` (hauler) -> `unload_cargo` (hauler at station)
- **Risk**: Medium -- integration bugs could hide between individually-passing unit tests

### 5. `_execute_upgrade_base()` edge cases (world.py:1812)
- **Status**: Partial coverage in test_resources.py (gas/water cost tests) but missing: wrong position, max level, all upgrade types
- **Risk**: Low-medium

### 6. Storm battery multiplier
- **Status**: Storm module has no tests for its effect on action costs
- **Logic**: `get_battery_multiplier()` returns 1.0 + (1.5 * intensity) during active storms
- **Risk**: Medium -- affects all battery-consuming actions

## Existing Test Patterns

- `unittest.TestCase` with manual setUp/tearDown to save/restore WORLD state
- Direct import of module-level functions and constants
- `world.state` accessor for World instance, `WORLD` dict for raw access
- No mocking of storm_mod in most tests (storm is clear by default)
