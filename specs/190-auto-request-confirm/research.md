# Research: Automatic Request Confirm

**Branch**: `190-auto-request-confirm` | **Date**: 2026-03-06

## No Outstanding Unknowns

All technical decisions were resolvable from codebase analysis. No external research was needed.

## Decision Log

### 1. Sync vs Async Architecture for Hazard Detection

- **Decision**: Two-layer approach — sync hazard detection in `world.py`, async confirm gate in `agent.py`
- **Rationale**: `execute_action()` is synchronous by design (engine contract, world.py lines 40-46). The confirmation flow requires `asyncio.Event` waiting. Splitting keeps each layer in its natural execution model.
- **Alternatives considered**:
  - Making `execute_action()` async: Too invasive, breaks every caller
  - Putting all logic in `world.py`: Impossible due to sync constraint
  - Middleware pattern: Over-engineered for 3 call sites

### 2. Where to Place the Confirm Gate

- **Decision**: Shared async helper function in `agent.py`, called from all three agent loops before `execute_action()`
- **Rationale**: All three loops (rover, drone, hauler) follow the same pattern of calling `execute_action()`. A shared helper avoids code duplication.
- **Alternatives considered**:
  - Decorator on `execute_action()`: Cannot make a sync function async via decorator
  - Separate module: Overkill for a single helper function

### 3. Battery Threshold Value

- **Decision**: 15% (0.15) as a fraction of max battery
- **Rationale**: This is the threshold specified in requirements. It's checked after computing the move cost (including storm multiplier and distance).
- **Alternatives considered**: 10% (too aggressive), 20% (too conservative)

### 4. Storm Intensity Threshold

- **Decision**: > 0.5 intensity triggers auto-confirm
- **Rationale**: Storm intensity ranges from 0.0 to 1.0. At 0.5+, battery multiplier is ~1.75x and move failure chance is ~7.5%. This represents meaningful danger.
- **Alternatives considered**: > 0.3 (too sensitive, would fire on every storm), > 0.7 (misses dangerous mid-range storms)

### 5. Geyser Destination Check Scope

- **Decision**: Check only the final destination tile, not intermediate tiles
- **Rationale**: The agent "teleports" through intermediate tiles in multi-tile moves (there is no per-step hazard application in the current engine). Geysers only damage agents standing on them at eruption time. Checking the final destination is the correct behavior.
- **Alternatives considered**: Check all intermediate tiles — but the engine doesn't process intermediate hazards for movement, so this would be inconsistent.

### 6. Confirmation Message Format

- **Decision**: Combine all detected hazards into a single descriptive message
- **Rationale**: The host enforces one-per-agent confirm limit. Multiple separate confirms would replace each other. A combined message gives the operator full context in one prompt.
- **Alternatives considered**: Separate confirms per hazard — but the one-per-agent enforcement in `host.py` makes this impossible without refactoring.
