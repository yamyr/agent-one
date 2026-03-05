# Research: Multi-Scenario Presets

**Branch**: `188-multi-scenario-presets` | **Date**: 2026-03-06

---

## R1: World Generation Constants

**Question**: Which constants can presets override?

**Findings**:
- `STONE_PROBABILITY = 0.025` — vein spawn chance per tile
- `ICE_PROBABILITY = 0.015` — ice deposit spawn chance per tile
- `MOUNTAIN_PROBABILITY = 0.004` — mountain obstacle spawn chance
- `GEYSER_PROBABILITY = 0.002` — geyser obstacle spawn chance
- These are module-level constants in `world.py`, used in `_generate_chunk()`
- Presets cannot change these directly (they are used at chunk generation time)
- Solution: presets modify WORLD dict entries post-generation for agents and storm, and use world_overrides that `apply_preset()` merges into WORLD

**Decision**: Presets override WORLD dict values (agents, storm settings) rather than chunk generation constants. For resource density, presets can modify stone/ice lists post-generation or adjust `TARGET_QUANTITY`.

---

## R2: Storm System Integration

**Question**: How do presets configure storm behavior?

**Findings**:
- `server/app/storm.py` has constants: `STORM_MIN_INTERVAL=30`, `STORM_MAX_INTERVAL=80`, `STORM_MIN_DURATION=10`, `STORM_MAX_DURATION=30`
- `make_storm_state()` returns the initial storm dict embedded in WORLD
- `schedule_next_storm(world)` picks random interval between MIN/MAX
- Presets can override WORLD["storm"]["next_storm_tick"] to schedule storms sooner
- For more aggressive storms, presets can set storm state to trigger immediate storms

**Decision**: `storm_survival` preset sets `WORLD["storm"]["next_storm_tick"]` to current tick + 5 (immediate storm) and description notes frequent storms. The storm system will naturally reschedule after each storm ends.

---

## R3: Agent Battery and Fuel Overrides

**Question**: How do presets adjust agent capabilities?

**Findings**:
- Agent battery is stored as `WORLD["agents"][agent_id]["battery"]` (0.0-1.0 fraction)
- Fuel capacity is a module-level constant (`FUEL_CAPACITY_ROVER = 350`)
- Agent position is `WORLD["agents"][agent_id]["position"]` as [x, y]
- `_make_rover(x, y)` creates default rover state at position

**Decision**: Presets can modify battery values in WORLD dict directly. Fuel capacity constants remain unchanged (too deeply embedded). `storm_survival` starts with lower battery (0.5). `resource_race` starts at full battery (1.0).

---

## R4: Active Agents Configuration

**Question**: How do presets control which agents are active?

**Findings**:
- `settings.active_agents` is a comma-separated string read at startup
- `_register_agents()` in `main.py` parses this and registers agents from `AGENT_MAP`
- When applying a preset via API, the reset flow is: `host.stop()` -> `reset_world()` -> `apply_preset()` -> `_register_agents()` -> `host.start()`

**Decision**: Presets include an optional `active_agents` override. When applying via API, temporarily override `settings.active_agents` before `_register_agents()`. The `cooperative` preset enables multiple rovers.

---

## R5: Reset Flow Integration

**Question**: Where does `apply_preset()` hook into the existing reset flow?

**Findings**:
- `reset_simulation()` in `main.py`: `host.stop()` -> `reset_world()` -> `narrator.reset()` -> `_register_agents()` -> `host.start()`
- `reset_world()` in `world.py`: increments generation_id, builds fresh world, clears indices, re-generates chunks, schedules storm

**Decision**: `apply_preset()` runs after `reset_world()` and before `_register_agents()`. It modifies WORLD dict in-place. The API endpoint follows the same reset flow with `apply_preset()` inserted.

---

## R6: Preset Data Structure

**Question**: What shape should preset definitions have?

**Decision**: Each preset is a dict with:
```python
{
    "name": str,
    "description": str,
    "world_overrides": {
        "storm": {...},           # merged into WORLD["storm"]
        "mission": {...},         # merged into WORLD["mission"]
    },
    "agent_overrides": {
        "rover-*": {"battery": float},  # applied to matching agents
    },
    "active_agents": str | None,  # override for settings.active_agents
}
```

This keeps presets declarative and easy to extend.
