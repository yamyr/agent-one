# Implementation Plan: Automatic Request Confirm

**Branch**: `190-auto-request-confirm` | **Date**: 2026-03-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/190-auto-request-confirm/spec.md`

## Summary

Add an automatic hazard-detection gate before move actions that triggers the existing human confirmation flow when dangerous conditions are detected (geyser at destination, low post-move battery, active high-intensity storm). This operates at the engine level for all movable agent types (rover, drone, hauler), independent of LLM reasoning. A config toggle `auto_confirm_enabled` (default `True`) controls the behavior.

## Technical Context

**Language/Version**: Python 3.14+
**Primary Dependencies**: FastAPI, pydantic-settings, mistralai
**Storage**: In-memory WORLD dict (no DB changes)
**Testing**: pytest (synchronous tests for hazard detection, async tests for confirm flow)
**Target Platform**: Linux/macOS server
**Project Type**: Web service (FastAPI backend)
**Performance Goals**: Hazard detection adds <1ms overhead per move action
**Constraints**: `execute_action()` is synchronous; confirm flow requires async. Detection logic must be synchronous and callable from both sync tests and async agent loops.
**Scale/Scope**: 3 agent types, 3 hazard conditions, 1 config toggle

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is a template (not customized). No project-specific gates to enforce.
General principles applied:
- Simplicity: Minimal code change — reuse existing `host.create_confirm()` and UI flow
- Test-first: Comprehensive test coverage planned for all hazard types
- No new dependencies required

**Gate status**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/190-auto-request-confirm/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── spec.md              # Feature specification
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── config.py          # MODIFIED: add auto_confirm_enabled setting
│   ├── world.py           # MODIFIED: add detect_move_hazards() function
│   ├── agent.py           # MODIFIED: add auto-confirm gate before execute_action() in all 3 agent loops
│   └── host.py            # UNCHANGED (reuse existing create_confirm/resolve_confirm)
└── tests/
    └── test_auto_confirm.py  # NEW: comprehensive tests for auto-confirm feature
```

**Structure Decision**: This is a surgical feature addition. Three existing files are modified (config, world, agent), one new test file is created. No new modules, no architectural changes.

## Complexity Tracking

No violations to justify — the implementation is minimal.

## Architecture Decision: Sync Detection + Async Gate

**Key constraint**: `execute_action()` in `world.py` is synchronous. The confirmation flow is async (creates an `asyncio.Event`, waits for human response via WebSocket).

**Decision**: Split the feature into two layers:
1. **Hazard detection** (`detect_move_hazards()` in `world.py`): A synchronous, pure function that takes agent state, destination, and world state, and returns a list of hazard descriptions. Zero side effects, easily testable.
2. **Async confirm gate** (helper in `agent.py`): An async function that calls `detect_move_hazards()`, and if hazards exist, creates a confirmation request via `host.create_confirm()`, waits for response, and returns whether to proceed.

This keeps `world.py` as a pure synchronous engine (honoring the existing contract at line 40-46) and puts the async orchestration in `agent.py` where it belongs.

**Alternatives rejected**:
- Making `execute_action()` async: Would require changes to every caller and break the sync engine contract.
- Adding confirm logic only in world.py: Impossible — async wait cannot happen in a sync function.

## Implementation Phases

### Phase 1: Config Toggle
- Add `auto_confirm_enabled: bool = True` to `Settings` in `config.py`

### Phase 2: Hazard Detection Function
- Add `detect_move_hazards(agent_id, agent, dest_x, dest_y, move_cost, world_state)` to `world.py`
- Returns `list[str]` of hazard descriptions (empty = safe)
- Checks:
  1. Geyser at destination with state "erupting" or "warning"
  2. Post-move battery < 0.15 (15%)
  3. Storm active with intensity > 0.5
- Uses existing `_obstacle_index` for O(1) geyser lookup
- Uses existing `storm_mod.get_storm_info()` for storm state

### Phase 3: Async Confirm Gate Helper
- Add `async _auto_confirm_gate(host, agent_id, action_name, params)` helper in `agent.py`
- Called before `execute_action()` in all three agent loops (rover, drone, hauler)
- Only fires for `action_name == "move"` and when `settings.auto_confirm_enabled` is True
- Computes destination and cost (replicating the same logic from `execute_action` to determine `tx, ty` and `cost`)
- Calls `detect_move_hazards()` — if empty, returns `None` (proceed)
- If hazards found: calls `host.create_confirm()` with combined message, broadcasts `confirm_request` event, waits with 30s timeout
- Returns `{"ok": False, "error": "..."}` if denied/timed out, or `None` if confirmed

### Phase 4: Integration into Agent Loops
- In rover loop (~line 2118): Before `execute_action()`, call `_auto_confirm_gate()`. If it returns a result, use that instead of calling `execute_action()`.
- In drone loop (~line 2473): Same pattern.
- In hauler loop (~line 2660): Same pattern.

### Phase 5: Tests
- New `test_auto_confirm.py` covering:
  - `detect_move_hazards()`: geyser erupting, geyser warning, geyser idle (no hazard), storm > 0.5, storm <= 0.5, low battery, battery ok, combined conditions
  - Config toggle: hazards detected but auto_confirm_enabled=False
  - Edge cases: no host, multi-tile move, station agent (never triggers)
