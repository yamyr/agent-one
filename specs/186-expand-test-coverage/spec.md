# Feature 186: Expand Test Coverage

## Summary

Cover untested code paths in the server: `collect_gas` action, `HaulerLoop` integration, station `recall_agent`, resource lifecycle chain (dig -> drop -> pickup -> unload), upgrade edge cases, and storm battery multiplier effects.

## User Stories

### US1 (P1): Core action tests -- collect_gas, recall, upgrade edge cases

**As a** developer, **I want** unit tests for `_execute_collect_gas`, station `recall_agent`, and `_execute_upgrade_base` edge cases **so that** regressions in these untested code paths are caught immediately.

#### Acceptance Criteria
- `collect_gas` success: adjacent gas plant with stored gas, battery deducted, inventory updated
- `collect_gas` failure: no adjacent gas plant, gas plant has no gas, insufficient battery
- `recall_agent` via station `execute_action`: returns ok with agent_id and reason
- `recall_agent` for non-existent agent: still returns ok (station action is a command, not world mutation)
- `upgrade_base` at wrong position: fails with position error
- `upgrade_base` already at max level: fails with max level error
- `upgrade_base` with all upgrade types: each succeeds with correct resource deduction

### US2 (P1): Agent loop tests -- HaulerLoop tick, event broadcasting

**As a** developer, **I want** tests for `HaulerLoop.tick()` integration **so that** the hauler's reason-execute-broadcast cycle is validated without requiring a live LLM.

#### Acceptance Criteria
- HaulerLoop tick executes a mocked reasoner action and calls `execute_action`
- Broadcast is called with action messages when action succeeds
- Goal confidence is updated after action execution
- Auto-charge triggers when hauler is at station with low battery

### US3 (P2): Integration tests -- resource lifecycle, storm effects

**As a** developer, **I want** end-to-end tests for the dig->drop->pickup->unload chain and storm battery cost multipliers **so that** cross-action workflows and environmental effects are validated.

#### Acceptance Criteria
- Full chain: rover digs vein -> drops item -> hauler picks up -> hauler unloads at station -> delivered_items updated
- Storm active increases battery cost for move, dig, collect_gas actions
- Storm clear has multiplier of 1.0
