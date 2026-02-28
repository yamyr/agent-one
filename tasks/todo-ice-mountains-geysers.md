# Ice Mountains & Air Geysers — Implementation Plan

## Overview

Add two new environmental hazards to the Mars simulation:
- **Ice Mountains**: Static, impassable terrain obstacles that force route-planning
- **Air Geysers**: Dynamic, intermittent eruption hazards that damage rovers and deflect drones

## Phase 1 — Backend Core (`server/app/world.py`)

- [x] Add constants: `MOUNTAIN_PROBABILITY=0.008`, `GEYSER_PROBABILITY=0.012`, `GEYSER_ACTIVE_TICKS=3`, `GEYSER_DORMANT_TICKS=8`, `BATTERY_COST_GEYSER_ROVER=8/FUEL_CAPACITY_ROVER`, `MOUNTAIN_CLUSTER_MAX=3`
- [x] Add `"obstacles": []` to `_build_initial_world()`
- [x] Add obstacle generation to `_ensure_chunk()` — mountains (with clustering) and geysers, skip origin chunk
- [x] Add `_obstacle_at(x, y)` helper — returns obstacle dict or None
- [x] Add `_update_geysers()` — tick geyser state machines (active↔dormant), return eruption events
- [x] Update `next_tick()` to call `_update_geysers()` and return `(tick, geyser_events)` tuple
- [x] Update `move_agent()` — block movement into mountains, deflect drones from active geysers, drain rover battery on active geysers
- [x] Update `get_snapshot()` to include obstacles filtered by fog-of-war (revealed tiles only)

## Phase 2 — Models & Context (`server/app/models.py`)

- [x] Add `ObstacleInfo` pydantic model (`type: str, position: list[int], active: bool | None`)
- [x] Add `nearby_obstacles: list[ObstacleInfo]` to `RoverComputed`
- [x] Update `observe_rover()` in `world.py` to populate `nearby_obstacles` (within reveal radius)
- [x] Update `_update_rover_tasks()` to add obstacle-aware hints ("Geyser erupting nearby", "Mountain blocks path")

## Phase 3 — Agent AI (`server/app/agent.py`)

- [x] Add `== Hazards ==` section to `RoverAgent._build_context()` listing nearby obstacles
- [x] Add obstacle avoidance rules to Rover system prompt
- [x] Add `== Hazards ==` section to `DroneAgent._build_context()` listing nearby obstacles
- [x] Add obstacle awareness rules to Drone system prompt
- [x] Update `_fallback_turn()` to filter out mountain-blocked directions

## Phase 4 — Agent Loop & Broadcasting (`server/app/agent.py`)

- [x] Update `RoverLoop.tick()` to capture `next_tick()` geyser events and broadcast eruptions
- [x] Update `DroneLoop.tick()` — reads tick passively (no `next_tick()` call to prevent double-ticking)

## Phase 5 — Frontend (`ui/src/`)

- [x] Add `OBSTACLE_COLORS` to `constants.js` (`ice_mountain: '#a0c8e8'`, `air_geyser_active: '#e04040'`, `air_geyser_dormant: '#8a6a4a'`)
- [x] Add obstacle rendering to `WorldMap.vue` — mountain triangles, geyser circles with active/dormant styling
- [x] Add `eruption` toast handler to `App.vue` `onSimEvent()`

## Phase 6 — Tests (`server/tests/test_world.py`)

- [x] `TestIceMountain`: test mountain blocks rover move, test mountain blocks drone move (4 tests)
- [x] `TestAirGeyser`: test active geyser drains rover battery, test active geyser deflects drone, test dormant geyser allows passage (4 tests)
- [x] `TestGeyserCycle`: test geyser transitions active→dormant→active correctly (3 tests)
- [x] `TestObstacleGeneration`: test chunk generates obstacles, test origin chunk has no obstacles, test mountain clustering (3 tests)
- [x] `TestSnapshot`: test obstacles included in snapshot (1 test)
- [x] Run full test suite — 308 passed ✅

## Post-Implementation

- [x] Update `Changelog.md`
- [ ] Commit with co-author trailer
- [ ] Create PR following semantic template
- [ ] Wait for CI, fix failures if any
- [ ] Add Eduardo as reviewer/approver
