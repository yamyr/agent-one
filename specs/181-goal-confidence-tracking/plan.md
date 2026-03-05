# Implementation Plan: Goal Confidence Tracking + UI Bars

**Branch**: `181-goal-confidence-tracking` | **Date**: 2026-03-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/181-goal-confidence-tracking/spec.md`

## Summary

Add a `goal_confidence` float (0.0–1.0) to every agent's state in the world model. Initialize at 0.5 on mission assignment. Update deterministically after each action (increase on success, decrease on failure/fallback/hazard). Expose in observation contexts (observe_rover, observe_hauler, observe_station), world snapshots (UI), and training data. Display as a color-coded animated bar in the AgentPane UI component.

## Technical Context

**Language/Version**: Python 3.14+ (server), JavaScript/Vue 3 (UI)
**Primary Dependencies**: FastAPI, Pydantic, Mistral AI SDK (server); Vue 3, Vite (UI)
**Storage**: SurrealDB (runtime), in-memory WORLD dict (simulation state)
**Testing**: pytest (server), manual + snapshot testing (UI)
**Target Platform**: Web application (localhost dev, Docker production)
**Project Type**: Web service (FastAPI backend) + SPA (Vue 3 frontend)
**Performance Goals**: Real-time WebSocket updates within 1 second of action completion
**Constraints**: Confidence updates must be deterministic (fixed increments), no time-based decay
**Scale/Scope**: 3-4 concurrent agents, single simulation instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is unpopulated (template only). No gates to evaluate. Proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/181-goal-confidence-tracking/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── websocket-schema.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── models.py            # Add goal_confidence to RoverAgentState, HaulerAgentState, RoverSummary
│   ├── world.py             # Add goal_confidence init, update logic, expose in observe_* and get_snapshot
│   ├── agent.py             # Capture confidence before/after in tick(), pass to training data
│   └── training_models.py   # Add goal_confidence fields to TurnWorldSnapshot, TrainingTurn
└── tests/
    └── test_goal_confidence.py  # Unit tests for confidence update logic

ui/
└── src/
    └── components/
        ├── ConfidenceBar.vue    # New component (cloned from BatteryBar pattern)
        ├── AgentPane.vue        # Add goalConfidence prop + ConfidenceBar usage
        └── AgentPanes.vue       # Add goalConfidence() helper, pass prop
```

**Structure Decision**: Existing web application structure (server/ + ui/). No new directories needed except `contracts/` in specs. All changes are additions to existing files plus one new Vue component and one new test file.

## Complexity Tracking

No constitution violations to justify.
