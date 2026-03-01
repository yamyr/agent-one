# Ice, Water, Gas & Hauler — Implementation Plan

## Overview

Add four interconnected resource mechanics and a new Hauler agent to the Mars simulation:

1. **Ice Resources**: Ice mountains already exist as obstacles — extend them to be harvestable
2. **Water Recycling**: Process ice into water at the station (or a water processor structure)
3. **Gas Plants**: Build gas plants on top of geysers to capture gas
4. **Hauler Agent**: New agent type specialized in material transport

## Architecture Decisions

- All new resources (ice, water, gas) extend the existing `inventory` system
- New actions plug into `execute_action()` in `world.py` following existing patterns
- Hauler agent follows the same `_make_agent()` → `AgentLoop` pattern as Rover/Drone
- New Pydantic models extend `models.py` for type safety
- World generation for ice deposits uses existing chunk-based procedural system

---

## Task Breakdown

### Task 1: Fix #131 — observe_rover() boundary check ✅
- **File**: `server/app/world.py`, line 1802
- **Change**: Remove `GRID_W/GRID_H` boundary check — infinite grid has no bounds
- **Risk**: LOW — isolated fix

### Task 2: New Resource Types in Models
- **File**: `server/app/models.py`
- **Add**: `ResourceType` enum (basalt_vein, ice, water, gas)
- **Add**: `GasPlantInfo` model
- **Add**: `HaulerContext` model (similar to `RoverContext`)
- **Update**: `InventoryItem` to support new resource types

### Task 3: Ice Resource System
- **File**: `server/app/world.py`
- **Constants**: `ICE_PROBABILITY`, `BATTERY_COST_GATHER_ICE`, ice quantity ranges
- **Chunk gen**: Mountains can optionally have ice deposits (new field on obstacle)
- **New action**: `gather_ice` — extract ice from a mountain obstacle (rover must be adjacent)
- **Inventory**: Ice items stored as `{"type": "ice", "quantity": N}`
- **Tool def**: Add `gather_ice` to `ROVER_TOOLS` in `agent.py`

### Task 4: Water Recycling
- **File**: `server/app/world.py`
- **New structure type**: `water_processor` — spawns near station
- **New action**: `process_ice` — convert ice inventory items to water at water processor
- **Conversion**: 1 ice → 1 water (water is more valuable, needed for base upgrades)
- **Tool def**: Add `process_ice` to `ROVER_TOOLS` in `agent.py`

### Task 5: Gas Plant on Geysers
- **File**: `server/app/world.py`
- **New action**: `build_gas_plant` — rover builds a gas plant on an adjacent geyser
- **Mechanics**: Gas plant converts geyser eruptions into collectible gas
- **Passive**: Active gas plants produce gas each eruption cycle (stored in structure)
- **New action**: `collect_gas` — rover collects accumulated gas from gas plant
- **Tool defs**: Add `build_gas_plant` and `collect_gas` to `ROVER_TOOLS`

### Task 6: Hauler Agent
- **Files**: `server/app/world.py`, `server/app/agent.py`, `server/app/host.py`, `server/app/main.py`
- **World**: `_make_hauler()` factory — larger inventory (6 slots), slower, no analyze/dig
- **Agent**: `HaulerAgent` class — LLM reasoner with transport-focused tools
- **Tools**: `move`, `pick_up_from`, `deliver_to`, `notify`
- **Host**: Register hauler in `ACTIVE_AGENTS`, add to agent loop
- **Config**: `hauler_interval` setting

### Task 7: Base Upgrade Mechanic
- **File**: `server/app/world.py`
- **New action**: `upgrade_base` — spend water/gas to upgrade station capabilities
- **Upgrades**: Faster charging, extended reveal radius, auto-repair
- **Station integration**: Track upgrade levels in station agent state

### Task 8: Pydantic v2 Refinements
- **File**: `server/app/models.py`
- **Add**: Proper enums for resource types, obstacle kinds, structure types
- **Add**: Discriminated union for message types if time permits

### Task 9: Tests & Verification
- Write tests for new actions (gather_ice, process_ice, build_gas_plant, collect_gas)
- Verify existing tests still pass
- Build verification

---

## File Impact Summary

| File | Changes |
|------|---------|
| `server/app/world.py` | Ice system, water processing, gas plants, hauler factory, base upgrades |
| `server/app/agent.py` | New tool definitions, HaulerAgent class |
| `server/app/models.py` | New Pydantic models (resources, hauler context, gas plant) |
| `server/app/host.py` | Register hauler agent |
| `server/app/main.py` | Hauler agent loop |
| `server/app/config.py` | Hauler config settings |
| `server/app/station.py` | Station upgrade tracking |
| `Changelog.md` | Document all changes |

---

## Implementation Order

1. Fix #131 (boundary check) — immediate, no dependencies
2. Models first (types, enums) — foundation for everything else
3. Ice → Water → Gas (resource chain, each builds on previous)
4. Hauler agent (uses established patterns)
5. Base upgrades (optional stretch)
6. Pydantic refinements (optional stretch)
7. Tests, changelog, PR
