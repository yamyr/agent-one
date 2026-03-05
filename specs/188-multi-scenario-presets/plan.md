# Implementation Plan: Multi-Scenario Presets

**Branch**: `188-multi-scenario-presets` | **Date**: 2026-03-06 | **Spec**: `specs/188-multi-scenario-presets/spec.md`

## Summary

Add preset simulation scenarios that configure the world with different challenges and agent configurations. Five presets: default, storm_survival, resource_race, exploration, cooperative. Presets override WORLD dict values (storm settings, agent batteries, mission targets) after world reset. REST API endpoints for listing and applying presets. Config integration for startup preset.

## Technical Context

**Language/Version**: Python 3.14+ (server)
**Primary Dependencies**: FastAPI, Pydantic v2, pydantic-settings
**Storage**: In-memory (PRESETS dict in presets.py, overrides applied to WORLD dict)
**Testing**: pytest with existing test patterns
**Scale/Scope**: 1 new file (presets.py), 1 new test file, 2 modified files (config.py, main.py)

## Constitution Check

- Feature branch: `188-multi-scenario-presets` (created)
- Test coverage: Required
- Changelog update: Required
- Co-authoring: `Co-Authored-By: agent-one team <agent-one@yanok.ai>`

## Project Structure

### Documentation

```text
specs/188-multi-scenario-presets/
├── plan.md              # This file
├── spec.md              # 3 user stories
├── research.md          # 6 research decisions (R1-R6)
├── data-model.md        # Entity definitions
├── quickstart.md        # Verification steps
└── tasks.md             # Task list
```

### Source Code (files affected)

```text
server/
├── app/
│   ├── presets.py        # NEW: PRESETS dict + apply_preset()
│   ├── config.py         # MODIFIED: add preset field to Settings
│   └── main.py           # MODIFIED: preset API endpoints + startup preset
├── tests/
│   └── test_presets.py   # NEW: preset tests
```

## Key Implementation Details

### 1. Preset Definitions (presets.py)

`PRESETS` dict with 5 entries. Each has name, description, world_overrides, agent_overrides, active_agents.

`apply_preset(preset_name, world_dict)` function:
- Looks up preset in PRESETS
- Merges world_overrides into world_dict (shallow merge per top-level key)
- Applies agent_overrides to matching agents in world_dict["agents"]
- Returns the preset dict for reference

### 2. API Endpoints (main.py)

- `GET /api/presets` — returns `[{name, description}]` for all presets
- `POST /api/presets/{name}/apply` — reset + apply preset + restart agents

### 3. Config Integration (config.py)

- `preset: str = "default"` field in Settings
- In `lifespan()`, after `_register_agents()`, if `settings.preset != "default"`, call `apply_preset()`

## Complexity Tracking

Low complexity. No new data structures beyond a static dict. No UI changes. Leverages existing reset_world() and WORLD dict patterns.
