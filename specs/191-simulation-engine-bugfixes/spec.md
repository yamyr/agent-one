# Spec: Simulation Engine Critical Bugfixes (#191)

## Problem Statement

The Mars simulation engine has 9 confirmed bugs across `world.py`, `agent.py`, and `station.py` that cause incorrect simulation behavior. These range from a critical tick-inflation bug (world time runs N× too fast) to broken tool routing and incorrect resource conversion logic. All bugs were identified through code audit — none are cosmetic; all affect simulation correctness.

## Bugs to Fix

### CRITICAL

1. **Tick inflation (N× speed)** — `next_tick()` is called inside every agent's `tick()` method (`RoverLoop`, `DroneLoop`, `HaulerLoop`). With N active agents, the world tick advances N times per real cycle. Storm frequency, geyser eruption timing, passive structure effects, and power budget checks all run at N× speed.
   - Files: `agent.py:2131`, `agent.py:2588`, `agent.py:2781`
   - Impact: Storms arrive/end too fast, geysers cycle too fast, passive charging is N× too generous.

2. **Rover tool whitelist missing `drop_item` and `request_confirm`** — `MistralRoverReasoner.run_turn()` and `HuggingFaceRoverReasoner.run_turn()` have a hardcoded whitelist of valid tool names. `drop_item` and `request_confirm` are defined in `ROVER_TOOLS` and visible to the LLM, but the reasoner silently discards them and raises `RuntimeError`. `request_confirm` is handled downstream in `RoverLoop.tick()`, but it never reaches there.
   - Files: `agent.py:1027-1044`, `agent.py:1532-1549`
   - Impact: LLM crashes when calling these tools; `request_confirm` human-in-the-loop is broken at the reasoner level.

### HIGH

3. **Mountain path checking only at destination** — `move_agent()` checks structures along the entire movement path (correct) but only checks mountains at the final destination tile. Multi-tile moves can pass through intermediate mountains.
   - File: `world.py:1213-1216`

4. **Ice auto-delivery conversion ratio mismatch** — `check_mission_status()` converts ice to water via `delivered_ice // ICE_TO_WATER_RATIO` (integer division, 1 ice → 0 water). The `_execute_recycle_ice()` tool converts via `quantity * ICE_TO_WATER_RATIO` (1 ice → 2 water). The two paths disagree by a factor of 4.
   - File: `world.py:2191`

5. **Drone scan auto-relay broken** — Two bugs: (a) checks `result.get("concentration")` but the scan result dict has no `concentration` key (should be `peak`), so auto-relay never fires; (b) hardcodes relay target to `"rover-mistral"`, ignoring all other rovers.
   - File: `agent.py:2647-2649`

### MEDIUM

6. **Station memory unbounded** — Station memory is appended via direct list append, bypassing `record_memory()`'s `MEMORY_MAX` cap. Over a long simulation, the station LLM context grows indefinitely.
   - File: `agent.py` (station memory appends in tick loops)

7. **Geyser only damages agents on first eruption tick** — Agent damage is inside the `obs["state"] != "erupting"` transition guard. Agents standing on an erupting geyser take damage only on the first tick of the eruption phase, not subsequent ticks. Agents moving onto an already-erupting geyser take no damage.
   - File: `world.py:1096-1148`

8. **Missing storm battery multiplier on several actions** — `investigate_structure`, `upgrade_building`, and `use_refinery` don't apply storm battery cost multiplier, unlike `analyze`, `dig`, `gather_ice`, and `scan`.
   - Files: `world.py:2426`, `world.py:2520`, `world.py:2600`

## Out of Scope

- UI changes
- New features
- Narrator bugs (lower priority, separate PR)
- Performance optimizations (e.g., deep-copy reduction)

## Success Criteria

- All 8 bugs fixed with minimal code changes
- Comprehensive tests for each fix (regression prevention)
- All existing tests pass
- Ruff format + lint clean
- CI green
