# Training Data Logging — Implementation Plan

## Objective
Log every agent decision, world state evolution, and session parameter as structured training data in SurrealDB. This enables:
1. **Replay**: reconstruct any session tick-by-tick
2. **Training**: fine-tune LLMs on successful agent trajectories (context → action → outcome)
3. **Analysis**: compare agent performance across sessions, identify optimal strategies

## Architecture

### Data Model (SurrealDB Tables)

#### 1. `training_session` — One record per simulation run
```
{
  id: ulid,
  started_at: datetime,
  ended_at: datetime | null,
  status: "running" | "success" | "failed" | "aborted",
  config: {
    world_seed: str,
    active_agents: [str],
    llm_turn_interval: float,
    target_quantity: int,
    grid_w: int, grid_h: int,
    fuel_capacity_rover: int,
    fuel_capacity_drone: int,
  },
  result: {
    total_ticks: int,
    basalt_collected: int,
    basalt_delivered: int,
    duration_seconds: float,
  } | null,
  tags: [str],           # user-defined labels for filtering
}
```

#### 2. `training_turn` — One record per agent tick (the core training row)
```
{
  id: ulid,
  session: record<training_session>,   # SurrealDB relation
  tick: int,
  agent_id: str,
  agent_type: "rover" | "drone" | "station",
  timestamp: datetime,

  # INPUT: what the agent saw (LLM context)
  context: str,                        # full LLM prompt text
  world_snapshot: {                    # structured state at decision time
    agent_position: [int, int],
    agent_battery: float,
    agent_inventory: [{type, grade, quantity}],
    agent_memory: [str],
    agent_tasks: [str],
    visible_stones: [str],
    mission_status: str,
    collected_quantity: int,
    target_quantity: int,
    distance_to_station: int,
  },

  # OUTPUT: what the agent decided
  thinking: str | null,                # LLM reasoning text
  action_name: str,                    # "move", "dig", "scan", etc.
  action_params: {},                   # tool call arguments
  
  # OUTCOME: what happened
  action_result: {},                   # engine result (ok, error, etc.)
  action_ok: bool,
  battery_before: float,
  battery_after: float,
  position_before: [int, int],
  position_after: [int, int],

  # META
  model: str,                          # LLM model used
  is_fallback: bool,                   # was mock/fallback used?
  llm_duration_ms: int | null,         # LLM call latency
}
```

#### 3. `training_event` — Significant world/mission events
```
{
  id: ulid,
  session: record<training_session>,
  tick: int,
  timestamp: datetime,
  source: str,                         # "rover-mistral", "station", "world", etc.
  event_type: str,                     # "mission_success", "charge", "vein_found", etc.
  event_name: str,
  payload: {},
}
```

#### 4. `training_world_snapshot` — Periodic full world state captures
```
{
  id: ulid,
  session: record<training_session>,
  tick: int,
  timestamp: datetime,
  world_state: {},                     # full WORLD dict snapshot (fog-filtered)
}
```

### Integration Points

1. **Session lifecycle** (in `host.py`):
   - `Host.start()` → create `training_session` record
   - `Host.stop()` / mission end → update session with result + ended_at

2. **Agent turns** (in `agent.py` — `RoverLoop.tick()` and `DroneLoop.tick()`):
   - Before LLM call: capture pre-state (position, battery, inventory)
   - After LLM call: capture thinking, action, model, duration, fallback flag
   - After execute_action: capture result, post-state
   - Write `training_turn` record

3. **Station turns** (in `host.py` — `station_startup()` and event handlers):
   - Capture context, thinking, actions taken
   - Write `training_turn` for each station decision

4. **Events** (in `host.py` — `broadcast()`):
   - Intercept significant events (mission status, charges, alerts)
   - Write `training_event` records

5. **World snapshots** (in `host.py`):
   - Every N ticks (configurable, default 10), capture full world state
   - Write `training_world_snapshot`

### New Files
- `server/app/training_logger.py` — Core logger class with DB persistence
- `server/app/training_models.py` — Pydantic models for training data
- `server/tests/test_training_logger.py` — Tests

### Config Additions (in `config.py`)
- `training_enabled: bool = True` — toggle training data collection
- `training_snapshot_interval: int = 10` — world snapshot every N ticks

### API Endpoints (in `views.py` or new router)
- `GET /api/training/sessions` — list all sessions
- `GET /api/training/sessions/{id}` — session detail + summary stats
- `GET /api/training/sessions/{id}/turns` — paginated turns for a session
- `GET /api/training/sessions/{id}/events` — events for a session
- `GET /api/training/sessions/{id}/export` — export session as JSONL for training

## Task Checklist

- [x] Create feature branch `feature/training-data-logging`
- [x] Add Pydantic models (`training_models.py`)
- [x] Add config settings (`training_enabled`, `training_snapshot_interval`)
- [x] Implement `TrainingLogger` class (`training_logger.py`)
  - [x] `start_session()` — create session record
  - [x] `end_session()` — finalize session
  - [x] `log_turn()` — log agent turn
  - [x] `log_event()` — log significant event
  - [x] `log_world_snapshot()` — periodic snapshot
  - [x] DB table creation (schema init)
- [x] Integrate into `Host.start()` / `Host.stop()`
- [x] Integrate into `RoverLoop.tick()` / `DroneLoop.tick()`
- [x] Integrate into station startup + event handling
- [x] Add API endpoints for training data retrieval
- [x] Write tests
- [x] Update Changelog.md
- [x] Create PR
