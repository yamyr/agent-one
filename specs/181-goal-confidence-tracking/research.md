# Research: Goal Confidence Tracking + UI Bars

**Branch**: `181-goal-confidence-tracking` | **Date**: 2026-03-05

## R1: Agent State Storage Pattern

**Decision**: Add `goal_confidence: float` as a top-level key in agent state dicts (same level as `battery`, `mission`, `position`).

**Rationale**: The world model stores agent state as plain Python dicts (`WORLD["agents"][id]`). All existing scalar state (battery, position) lives at the top level. Adding `goal_confidence` at the same level is consistent, requires no new nested structures, and flows automatically through `get_snapshot()` → WebSocket → UI since the snapshot is a deep copy of the WORLD dict.

**Alternatives considered**:
- `goals: list[dict]` with per-goal confidence — rejected because the spec explicitly scopes this as a single per-agent value, not per-sub-goal. Would add unnecessary complexity.
- Separate `confidence_history: list` for tracking over time — rejected as out of scope. Training data already captures before/after per turn.

## R2: Confidence Update Strategy

**Decision**: Fixed-increment updates applied in the agent tick loop, after `execute_action()` returns and before broadcasting.

**Rationale**: The action result dict already contains `ok: bool`. The increment approach is deterministic, testable, and aligns with the spec assumption of "fixed increments that can be tuned later."

**Update table**:

| Trigger | Direction | Magnitude | Location |
|---------|-----------|-----------|----------|
| Action succeeds (`action_ok=True`) | +increase | +0.05 | `RoverLoop.tick()` after execute_action |
| Action fails (`action_ok=False`) | -decrease | -0.05 | `RoverLoop.tick()` after execute_action |
| Fallback turn (`is_fallback=True`) | -decrease | -0.08 | `RoverLoop.tick()` fallback path |
| Storm/hazard event | -decrease | -0.08 | `RoverLoop.tick()` storm check path |
| Mission assigned/reassigned | =reset | =0.50 | Mission assignment code in world.py |
| Successful delivery | +increase | +0.10 | Inside execute_action deliver result |

**Alternatives considered**:
- Probabilistic updates (random magnitude within range) — rejected for non-determinism in tests.
- LLM-reported confidence (agent self-reports) — rejected as separate concern; this feature is system-tracked confidence.
- Time-based decay per tick — rejected per spec assumption ("no time-based decay").

## R3: Observation Context Integration

**Decision**: Add `goal_confidence: float` field to `RoverAgentState`, `HaulerAgentState` Pydantic models. These models are already used in `observe_rover()` and `observe_hauler()` to build the LLM context.

**Rationale**: The observation functions construct Pydantic model instances from the agent state dict. Adding the field to the model means it automatically appears in the serialized context sent to the LLM. No separate plumbing needed.

**Key code paths**:
- `world.py:observe_rover()` (line ~3108) → constructs `RoverAgentState` → passed to reasoner
- `world.py:observe_hauler()` (line ~3170) → constructs `HaulerAgentState` → passed to reasoner
- `world.py:observe_station()` (line ~3204) → constructs `RoverSummary` per non-station agent → `RoverSummary` needs `goal_confidence` so station sees rover confidence

## R4: UI Rendering Pattern

**Decision**: Create `ConfidenceBar.vue` by cloning the `BatteryBar.vue` pattern. Adjust color thresholds per spec: green (0.7-1.0), amber (0.4-0.69), red (0.0-0.39).

**Rationale**: BatteryBar is a proven, lightweight component (props: `level` 0-1 float, computed: `pct`, `barColor`, template: track + fill + label). The confidence bar has identical data shape. Reusing the pattern ensures visual consistency and minimal code.

**BatteryBar color thresholds** (existing): green >60%, amber >30%, red <=30%
**ConfidenceBar color thresholds** (spec): green >=70%, amber >=40%, red <40%

**Data flow** (already proven for battery):
```
WORLD["agents"][id]["goal_confidence"]
  → get_snapshot() deep copy
  → broadcaster.send() via WebSocket
  → useWebSocket composable: worldState.value = event.payload
  → AgentPanes: reads worldState.agents[id].goal_confidence
  → AgentPane prop: :goal-confidence="..."
  → ConfidenceBar component renders bar
```

No new WebSocket events or message types needed — data piggybacks on the existing `state` snapshot broadcast.

## R5: Training Data Integration

**Decision**: Add `goal_confidence` to `TurnWorldSnapshot` and add `goal_confidence_before`/`goal_confidence_after` to `TrainingTurn`.

**Rationale**: Training data already captures `battery_before`/`battery_after` and `position_before`/`position_after`. Goal confidence follows the same pattern. The capture point is already in `RoverLoop.tick()` where `pre_rover` and `post_rover` agent states are read.

**Key integration point**: `agent.py` lines ~2065-2083 where `TrainingTurn` is constructed.

## R6: Station Agent Observation

**Decision**: Add `goal_confidence: float = 0.5` to `RoverSummary` model so the station agent sees rover/hauler/drone confidence levels.

**Rationale**: `observe_station()` builds `RoverSummary` for each non-station agent. The station uses these summaries to make coordination decisions. Adding confidence enables the station to prioritize helping low-confidence agents.

**Integration point**: `world.py:observe_station()` line ~3204 where `RoverSummary` is constructed.
