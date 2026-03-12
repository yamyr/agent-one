# Round 3 — UI Polish (All Phases)

## Phase 2: Zoom Fix & EventLog Virtualization
- [x] Dynamic viewport tile count based on zoom level
- [x] Zoom re-centering, MiniMap navigation, dead code cleanup
- [x] EventLog virtual scrolling with UID-based animations
- [x] Build passes, code review complete, PR #52 merged

## Phase 4: Toast Dedupe & Rate-Limiting (US2)
- [x] T006: Deduplication — identical messages increment count instead of duplicating
- [x] T007: Rate-limiting — MAX_VISIBLE=5, oldest evicted when full
- [x] T008: Count badge — `×N` rendered inline with toast message
- [x] T009: Build verification passed

## Phase 6: Loading Skeletons (US4 — remaining)
- [x] T016: EventLog skeleton state — 6 pulsing rows with staggered animation
- [x] T018: Build verification passed

## Phase 9: Polish
- [x] T025: Full build verification

---

# Implementation Plan: New Features & Polish (Round 4)

**Status: COMPLETED** (most items merged via PRs #235, #236, #238)


## Priority 1: Security Audit ✅
- [x] Scan for leaked secrets, API keys, sensitive info
- [x] Result: NO leaked secrets found. All API keys use env vars properly.
- [x] `.env` is gitignored, README has placeholder values only

## Priority 1b: Harden .gitignore
- [x] Add `.env.*`, `*.pem`, `*.key`, `training_data/` patterns

## Priority 2: Research & Design Review ✅
- [x] Investigate closed issues — all 50 resolved with merged PRs
- [x] Investigate open issues — #131 (observe_rover boundary), #93 (station error handling)
- [x] ROADMAP gaps identified: allocate_power, PowerBudgetWarning, confidence bars, scripted timeline, UiRequest::Confirm

## Priority 2b: Fix Critical Bug #131
- [x] Remove GRID_W/GRID_H boundary check in `observe_rover()` at world.py line 1802

## Priority 3a: Rover Upgrades — Base, Buildings, Ice
- [x] Add `ice_deposit` as a new resource type in world generation (spawns in outer chunks)
- [x] Add `gather_ice` rover action: picks up ice at current tile (costs 4 fuel)
- [x] Add `upgrade_base` rover action: deposit materials at station to improve station capabilities
- [x] Enhance building exploration: make broken_hauler and broken_manipulator functional
  - [x] broken_hauler: repairable, adds +2 inventory capacity to repairing rover
  - [x] broken_manipulator: repairable, enables building new structures

## Priority 3b: Ice → Water Recycling
- [x] Add `water_recycler` structure type (buildable at station)
- [x] Add `recycle_ice` action: converts ice into water at the recycler (3 ice → 1 water)
- [x] Water serves as secondary mission resource
- [x] Track water in mission state alongside basalt

## Priority 3c: Gas Plants on Geysers
- [x] Add `build_gas_plant` rover action: constructs gas plant ON a geyser tile
- [x] Gas plant converts geyser eruptions into collectible gas (no longer damages agents)
- [x] Add `gas` as resource type, tracked in mission
- [x] Gas plants are permanent structures with passive gas production each tick

## Priority 3d: Hauler Agent
- [x] Create `HaulerAgent` reasoner and `HaulerLoop` (BaseAgent subclass)
- [x] Hauler tools: `move` (max 5 tiles), `load` (transfer items from rover), `unload` (deposit at station)
- [x] Hauler has larger inventory (max 8 items) but cannot dig/analyze
- [x] Add hauler to world init, config, and UI
- [x] Hauler system prompt: optimized for logistics

## Priority 3e: Pydantic Refactor
- [ ] Use discriminated unions for message types
- [ ] Add model_validators for world state consistency
- [ ] Type resources with Pydantic models (ResourceType enum, ResourceDeposit model)
  **Partial** — ResourceType enum, typed context models done. Remaining: discriminated unions for message types, model_validators for world state consistency.

## Priority 4: Attribution
- [x] Configure git to attribute commits to 'yamyr'
- [x] Ensure all new commits use proper co-author trailer

---

# Task Plan: Rover-Driven Base Upgrade System

## Scope
- [x] Add station upgrade definitions and execution flow in `server/app/world.py`
- [x] Apply upgrade effects to charge rate, rover fuel capacity, reveal radius, and repair behavior
- [x] Track salvaged vehicle parts in `WORLD["station_resources"]["parts"]`
- [x] Expose upgrade tool and upgrade status/cost visibility in rover LLM context (`server/app/agent.py`)
- [x] Add typed upgrade metadata to rover world models (`server/app/models.py`)

## Validation
- [ ] Update/extend tests for new upgrade contract and salvage behavior
- [ ] Run diagnostics on changed files
- [ ] Run server test suite and confirm pass

## Review Notes
- [ ] Document what changed and key edge cases covered

---

# Feature: Scripted Event Timeline (#191)

## Overview

Add a scripted event timeline engine that fires pre-defined world events at specific
simulation ticks. This enables deterministic demo scenarios, tutorial walkthroughs,
and repeatable integration testing without relying on random storm/geyser timing.

## Design

### Core concept
A **ScriptedTimeline** reads an ordered list of `ScriptedEvent` entries, each with:
- `tick`: simulation tick to fire the event at
- `type`: event type (storm_start, storm_end, resource_spawn, battery_drain,
  agent_message, custom_broadcast, etc.)
- `payload`: dict of event-specific parameters

### Architecture decisions
- **New module** `server/app/events.py` — self-contained, no modifications to storm.py
- **Integration point**: Host calls `timeline.check_tick(tick)` each simulation tick
- **Config**: `event_script` setting in config.py for script file path (JSON)
- **API**: REST endpoints to load/query/clear the timeline at runtime
- **Preset integration**: A `demo_timeline` preset loads a curated script

### Event types supported
1. `storm_start` — force a storm warning at the given tick
2. `storm_end` — force-clear an active storm
3. `resource_spawn` — place a vein/ice/gas at a specific position
4. `battery_drain` — drain a specific agent's battery
5. `battery_set` — set a specific agent's battery level
6. `agent_message` — inject a message into an agent's inbox
7. `broadcast` — emit an arbitrary event to all WebSocket clients
8. `spawn_obstacle` — place a mountain or geyser at a position
9. `mission_update` — modify mission target or collected quantity

## Tasks

- [x] Create feature spec & plan
- [ ] Implement `ScriptedEvent` and `ScriptedTimeline` in `server/app/events.py`
- [ ] Add `event_script` config setting
- [ ] Integrate timeline into Host tick loop
- [ ] Add REST API endpoints (`/api/timeline/*`)
- [ ] Add `demo_timeline` preset with sample script
- [ ] Write comprehensive tests (`server/tests/test_events.py`)
- [ ] Run ruff format/check + full test suite
- [ ] Update Changelog.md
- [ ] Commit, push, open PR
