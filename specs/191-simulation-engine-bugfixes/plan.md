# Plan: Simulation Engine Critical Bugfixes (#191)

## Approach

Minimal, surgical fixes to 8 confirmed bugs in the simulation engine. Each fix is independent and testable in isolation. No refactoring, no new features — pure correctness fixes.

## Fix Strategy

### 1. Tick Inflation (CRITICAL)

**Current:** Each agent loop (`RoverLoop.tick()`, `DroneLoop.tick()`, `HaulerLoop.tick()`) calls `next_tick()` which increments `WORLD["tick"]` and runs passive effects. With N agents, tick advances N× per real cycle.

**Fix:** Replace per-agent `next_tick()` calls with a time-based tick guard. Add a `_last_tick_time` sentinel to the world dict. `next_tick()` becomes idempotent within a time window — only the first caller per cycle actually advances the tick. Subsequent callers within the same window get the current tick without advancing.

**Why this approach:** Minimal change to agent loop structure. No need to refactor into a central tick orchestrator. Agents keep their existing loop pattern.

### 2. Tool Whitelist (CRITICAL)

**Fix:** Add `"drop_item"` and `"request_confirm"` to the tool name whitelist in both `MistralRoverReasoner.run_turn()` and `HuggingFaceRoverReasoner.run_turn()`.

### 3. Mountain Path Checking (HIGH)

**Fix:** Move the mountain/obstacle check inside the existing path-walking loop in `move_agent()`, alongside the structure check.

### 4. Ice Conversion Ratio (HIGH)

**Fix:** Change `check_mission_status()` line 2191 from `delivered_ice // ICE_TO_WATER_RATIO` to `delivered_ice * ICE_TO_WATER_RATIO` to match the recycle tool's conversion.

### 5. Drone Scan Auto-Relay (HIGH)

**Fix:** (a) Change `result.get("concentration", 0)` to `result.get("peak", 0)`. (b) Relay to all active rovers, not just `"rover-mistral"`.

### 6. Station Memory Cap (MEDIUM)

**Fix:** Use `record_memory("station", ...)` instead of direct `mem.append()` for station memory additions. This routes through the existing `MEMORY_MAX` cap.

### 7. Geyser Per-Tick Damage (MEDIUM)

**Fix:** Add a second damage check outside the state-transition guard, so agents on erupting geysers take damage every tick of the eruption phase.

### 8. Storm Multiplier on Missing Actions (MEDIUM)

**Fix:** Apply `storm_mult` to battery costs in `_execute_investigate_structure()`, `_execute_upgrade_building()`, and `_execute_use_refinery()`.

## Testing Strategy

One test class per fix. Tests verify:
- The bug existed (regression guard)
- The fix works correctly
- Edge cases are covered

## Risk Assessment

- **Tick fix:** Low risk — idempotent guard, no behavioral change to agents
- **Tool whitelist:** Zero risk — additive change
- **Mountain path:** Low risk — moves existing check into existing loop
- **Ice conversion:** Low risk — single line arithmetic fix
- **Drone relay:** Low risk — key name fix + loop over agents
- **Station memory:** Zero risk — uses existing capped function
- **Geyser damage:** Low risk — additive damage check
- **Storm multiplier:** Low risk — follows established pattern from other actions
