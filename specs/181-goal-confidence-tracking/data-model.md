# Data Model: Goal Confidence Tracking

**Branch**: `181-goal-confidence-tracking` | **Date**: 2026-03-05

## Entity Changes

### Agent State Dict (world model — plain dict)

**New field added to all agent types** (rover, hauler, drone, station):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_confidence` | `float` | `0.5` | Current confidence in active mission (0.0-1.0) |

**Initialization**: Set to `0.5` in `_make_rover()`, `_make_hauler()`, `_make_drone()`, and station init.

**Reset trigger**: Set to `0.5` whenever a new mission is assigned.

**Clamping**: Always clamped to `[0.0, 1.0]` after any update.

### Pydantic Models (server/app/models.py)

#### RoverAgentState — add field

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_confidence` | `float` | `0.5` | Agent's confidence in current mission |

#### HaulerAgentState — add field

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_confidence` | `float` | `0.5` | Agent's confidence in current mission |

#### RoverSummary — add field

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_confidence` | `float` | `0.5` | Agent's confidence (visible to station) |

### Training Models (server/app/training_models.py)

#### TurnWorldSnapshot — add field

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_confidence` | `float` | `0.5` | Agent's confidence at snapshot time |

#### TrainingTurn — add fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_confidence_before` | `float` | `0.5` | Confidence before action |
| `goal_confidence_after` | `float` | `0.5` | Confidence after action |

## Confidence Update Rules

### Increment Table

| Event | Delta | Rationale |
|-------|-------|-----------|
| Action success | +0.05 | Steady progress signal |
| Action failure | -0.05 | Symmetric penalty |
| Fallback turn | -0.08 | Larger penalty — agent couldn't reason a useful action |
| Storm/hazard | -0.08 | External disruption lowers mission viability |
| Successful delivery | +0.10 | Major milestone toward mission completion |
| Mission reassigned | =0.50 | Full reset — new mission, fresh assessment |

### State Transitions

```
Mission Assigned → goal_confidence = 0.5
  ↓
Action Loop:
  success  → goal_confidence = clamp(gc + 0.05, 0.0, 1.0)
  failure  → goal_confidence = clamp(gc - 0.05, 0.0, 1.0)
  fallback → goal_confidence = clamp(gc - 0.08, 0.0, 1.0)
  hazard   → goal_confidence = clamp(gc - 0.08, 0.0, 1.0)
  deliver  → goal_confidence = clamp(gc + 0.10, 0.0, 1.0)
  ↓
Mission Reassigned → goal_confidence = 0.5 (reset)
```

## Data Flow

```
[World Model]                    [Server]                     [Client]
agents[id]["goal_confidence"]
        │
        ├──→ observe_rover()  → RoverAgentState.goal_confidence → LLM prompt
        ├──→ observe_hauler() → HaulerAgentState.goal_confidence → LLM prompt
        ├──→ observe_station()→ RoverSummary.goal_confidence → Station LLM prompt
        ├──→ get_snapshot()   → snapshot["agents"][id]["goal_confidence"] → WebSocket → UI
        └──→ TrainingTurn     → goal_confidence_before/after → training log
```
