# Abandoned Structures Feature Plan

## Overview
Add abandoned buildings and vehicles to the Mars simulation that spawn within 10 tiles of base (0,0), serve as obstacles, and provide interactive gameplay elements.

## Structures

| Type | Category | Behavior |
|------|----------|----------|
| Refinery | Building | Extract valuable materials from Basalt veins in inventory |
| Solar Panel (Structural) | Building | +1% battery per 2 seconds when rover is within 1 tile |
| Accumulator | Building | +20% base capacity, recharges rover +1% every 5 seconds |
| Broken Hauler | Vehicle | Can be investigated; transports materials (obstacle) |
| Broken Manipulator | Vehicle | Can be investigated; builds infrastructure (obstacle) |

## Implementation Tasks

### Phase 1: Backend — World Model (`server/app/world.py`)
- [x] Add structure constants and type definitions
- [x] Add `"structures"` list to `_build_initial_world()`
- [x] Create `_spawn_abandoned_structures()` for deterministic placement within 10 tiles of base
- [x] Add `_find_structure_at(x, y)` helper
- [x] Add obstacle collision checking to `move_agent()` — block movement through structure tiles
- [x] Implement `_execute_investigate_structure()` — explore structures to reveal details
- [x] Implement `_execute_use_refinery()` — process basalt from inventory
- [x] Implement passive solar panel proximity effect (+1% per 2s within 1 tile) in tick/move
- [x] Implement passive accumulator effect (+1% per 5s when rover is nearby)
- [x] Register new actions in `execute_action()` dispatcher
- [x] Add structures to `get_snapshot()` with fog-of-war filtering
- [x] Add structures to `observe_rover()` context
- [x] Add structures to `_update_rover_tasks()` for task suggestions

### Phase 2: Backend — Agent Tools (`server/app/agent.py`)
- [x] Add `INVESTIGATE_STRUCTURE_TOOL` definition
- [x] Add `USE_REFINERY_TOOL` definition
- [x] Add tools to `ROVER_TOOLS` list
- [x] Update tool validation in `run_turn()` to accept new tool names
- [x] Update `_build_context()` with "Nearby structures" section
- [x] Add structure interaction rules to rover system prompt

### Phase 3: Frontend
- [x] Add structure colors/sizes to `ui/src/constants.js`
- [x] Add SVG rendering for structures in `WorldMap.vue` with distinct shapes per type
- [x] Add visibility functions for structures
- [x] Add structures section to `MapLegend.vue`

### Phase 4: Tests (`server/tests/test_world.py`)
- [x] Test structure spawning (within 10 tiles, correct types, deterministic)
- [x] Test obstacle blocking (movement blocked through structure tiles)
- [x] Test `investigate_structure` action
- [x] Test `use_refinery` action
- [x] Test passive solar panel proximity charging
- [x] Test passive accumulator recharging

### Phase 5: Documentation & PR
- [x] Update `Changelog.md`
- [x] Commit with co-author trailer
- [x] Push and create PR assigned to schettino72

## Data Shape

```python
# Structure definition
{
    "type": "refinery",  # refinery | solar_panel_structure | accumulator | broken_hauler | broken_manipulator
    "category": "building",  # building | vehicle
    "position": [x, y],
    "explored": False,  # whether agent has investigated it
    "active": False,  # whether it's been activated
    "description": "An abandoned refinery for extracting materials from basalt",
    "contents": {},  # type-specific data (e.g., refinery has processing_capacity)
}
```

## Spawn Rules
- All structures spawn within Manhattan distance 10 from (0,0)
- No structure spawns at (0,0) — that's the station
- No structure overlaps with existing stones or other structures
- Deterministic: same world_seed produces same structure placement
- 5 structures total (one of each type)

## Obstacle Rules
- Agents CANNOT move through tiles containing structures
- Movement is blocked on a per-tile basis during the `move_agent()` path check
- Agents can be adjacent to structures and interact with them

## Passive Effects (tick-based)
- **Solar Panel Structure**: Every 2 seconds (ticks), rovers within 1 tile gain +1% battery
- **Accumulator**: Every 5 seconds (ticks), rovers within range gain +1% battery; base capacity conceptually +20%
