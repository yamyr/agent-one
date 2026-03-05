# Feature Specification: Multi-Scenario Presets

**Branch**: `188-multi-scenario-presets`
**Date**: 2026-03-06
**Status**: IDEA.md lists presets as a stretch goal; no implementation exists

---

## Problem Statement

The simulation always starts with the same default configuration. Operators and viewers cannot easily switch between different challenge modes (storm-heavy, resource-race, exploration, cooperative). Presets allow one-click scenario switching that reconfigures world generation probabilities, agent battery settings, and storm behavior.

## User Stories

### US1 (P1): Preset Definitions and Application Logic
**As a** simulation operator, **I want** predefined scenario presets that override world and agent settings, **so that** I can quickly switch between different challenge modes.

**Acceptance Criteria**:
- `PRESETS` dict in `server/app/presets.py` with 5 preset definitions: `default`, `storm_survival`, `resource_race`, `exploration`, `cooperative`
- Each preset has: `name`, `description`, `world_overrides` (probabilities, storm settings), `agent_overrides` (battery, fuel capacity), `active_agents` list override
- `apply_preset(preset_name, world_dict)` modifies the WORLD dict in-place
- `default` preset applies no changes (identity operation)
- Unknown preset name raises `ValueError`

### US2 (P1): API Endpoints for Preset Management
**As a** frontend client, **I want** REST endpoints to list and apply presets, **so that** the UI can offer scenario selection.

**Acceptance Criteria**:
- `GET /api/presets` returns list of presets with name and description
- `POST /api/presets/{name}/apply` applies preset: stops host, resets world, applies preset overrides, re-registers agents, starts host
- Apply endpoint returns `{ok: true, preset: name}` on success
- Apply endpoint returns `404` for unknown preset name

### US3 (P2): Config Integration for Startup Preset
**As a** deployment operator, **I want** to set a default preset via environment variable, **so that** the simulation starts with a specific scenario without manual API calls.

**Acceptance Criteria**:
- `preset: str = "default"` field added to `Settings` in `config.py`
- On startup, if `preset != "default"`, `apply_preset()` is called after world initialization
- Setting `PRESET=storm_survival` in `.env` starts the simulation in storm survival mode

## Scope

### In Scope
- Preset definitions with world and agent overrides
- `apply_preset()` function that modifies WORLD dict
- REST endpoints for listing and applying presets
- Config integration for startup preset
- Tests for definitions, application logic, and API endpoints

### Out of Scope
- UI preset selection component (future feature)
- Custom user-defined presets
- Preset persistence to database
- Mid-simulation preset switching without reset
- Preset-specific scoring or leaderboards
