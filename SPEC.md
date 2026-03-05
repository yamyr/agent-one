# Agent One: System Specification

Multi-agent LLM-powered Mars mission simulation. Autonomous agents (Rover, Drone, Hauler, Station) collaborate on a procedurally generated Mars surface, coordinated by a central Host. Each agent runs its own LLM reasoning loop to observe, decide, and act. A dual-narrator system provides live commentary, and a training data pipeline captures every decision for fine-tuning.

---

## 1. Architecture

```
+--------------------+
|   Base / Control   |   <-- human operator: assigns missions, monitors, voice commands, confirms high-risk actions
+--------------------+
        |
        v
+--------------------+       +--------------------+
|       Host         |       |     Narrator       |
| Message Router     |       | Dual-narrator      |
| Agent Lifecycle    |       | Mistral + ElevenLabs|
| Confirmation Mgmt  |       | Streaming dialogue |
+--------------------+       +--------------------+
        |
        v
+----------+ +----------+ +----------+ +----------+
|  Rover   | |  Drone   | | Hauler   | | Station  |
| Move/Dig | |  Scan    | | Load     | | Charge   |
| Analyze  | |  Map     | | Unload   | | Allocate |
| Ice/Gas  | |  Relay   | | Transport| | Mission  |
| Upgrade  | |          | |          | | Recall   |
| Peer Msg | |          | |          | | Power    |
+----------+ +----------+ +----------+ +----------+
        |                       |
        v                       v
+--------------------+   +--------------------+
| Training Pipeline  |   |   Voice Command    |
| SurrealDB tables   |   | Voxtral + LLM     |
| JSONL export       |   | Audio -> Command   |
+--------------------+   +--------------------+
```

- **Host**: Pure message router. Manages agent inboxes, lifecycle (start/stop/pause), station action routing, and human confirmation flow. Agents never communicate directly. The Host has no domain knowledge.
- **Agents**: `rover-mistral` (+ `rover-2`, `rover-large`, `rover-medium`, `rover-codestral`, `rover-ministral`, `rover-magistral`), `drone-mistral`, `hauler-mistral`, `station`. Each runs an observe -> reason (LLM) -> act -> update-confidence loop via `BaseAgent.tick()`.
- **World Model**: Python dict holding the chunk-based grid, stones, ice deposits, gas plants, agent positions/battery/inventory, storm state, structures, obstacles, and simulation state. Updated by tool call results and external events.
- **Broadcaster**: Singleton for WebSocket fan-out to connected UI clients.
- **Narrator**: Dual-narrator dialogue engine (Commander Rex + Dr. Nova) generating live commentary via Mistral LLM + ElevenLabs TTS.
- **Training Pipeline**: SurrealDB-backed logger recording every agent turn, event, and world snapshot for replay and fine-tuning.

### 1.1 LLM Backend Selection

The `agent_backend` configuration toggle selects the LLM reasoning backend:

| Backend | Config Value | Description |
|---------|-------------|-------------|
| Chat Completions | `chat_completions` (default) | Standard `client.chat.complete()` calls with tool definitions |
| Agents API | `agents_api` | Mistral Agents API (`client.beta.agents.create()`) with persistent conversation threads |

When `agents_api` is selected, the main rover/drone/station agents are automatically swapped for their Agents API equivalents. The `agents_api_persist_threads` toggle (default `True`) controls whether conversation threads persist across turns for cross-turn memory continuity.

---

## 2. World Model

### 2.1 Chunk-Based Infinite Grid

The world is an infinite 2D grid divided into chunks. Each chunk is `CHUNK_SIZE x CHUNK_SIZE` (16x16) tiles. Chunks generate procedurally with deterministic seeds as agents explore.

- Positions are `(x, y)` integer coordinates (no zone IDs)
- The origin chunk at `(0, 0)` is guaranteed to contain at least one basalt vein
- World bounds expand dynamically as agents move into unexplored areas
- No predefined map edges; the world grows with exploration
- Deterministic chunk seeds: `SHA256(world_seed:cx:cy)` ensures same seed produces same layout

### 2.2 Fog-of-War

Agents reveal tiles within their visibility radius:

| Agent  | Reveal Radius |
|--------|---------------|
| Rover  | 3 tiles       |
| Drone  | 6 tiles       |
| Hauler | 2 tiles       |

Unexplored tiles remain hidden until an agent moves close enough. Previously revealed tiles stay visible. Storm conditions reduce effective visibility by 40%.

### 2.3 Stones and Veins

Stones are basalt veins embedded in the terrain (spawn probability: 2.5% per tile). Each vein has a grade that determines its basalt quantity:

| Grade    | Rarity           | Basalt Quantity |
|----------|------------------|-----------------|
| low      | Common           | 10-50           |
| medium   | Uncommon         | 51-150          |
| high     | Rare             | 151-350         |
| rich     | Very rare        | 351-700         |
| pristine | Extremely rare   | 701-1000        |

Rarity follows weighted distribution. Veins start with `"unknown"` type and grade until analyzed by a rover.

### 2.4 Resource Economy

Beyond basalt, the simulation features a full resource chain:

| Resource | Source | Processing | Use |
|----------|--------|------------|-----|
| Ice | Ice deposits near mountains | Recycle at station -> Water | Water for upgrades |
| Water | Recycled from ice (2:1 ratio) | Station storage | Base upgrade costs |
| Gas | Gas plants built on geysers | Collected from plant | Base upgrade costs |
| Basalt | Dug from analyzed veins | Delivered to station | Primary mission objective |

**Ice deposits** spawn adjacent to mountains (probability-based). Rovers gather ice with `gather_ice` or `harvest_ice`, then recycle it at the station into water.

**Gas geysers** cycle through idle -> warning -> erupting phases. Rovers build `gas_plant` structures on geysers (costs 5 station water + 8 fuel). Plants accumulate gas on each eruption (5 gas/eruption). Rovers collect stored gas with `collect_gas`.

### 2.5 Obstacles and Structures

**Mountains** (0.4% spawn rate): Impassable terrain obstacles.

**Geysers** (0.2% spawn rate): Cycle through phases on a tick-based timer:
- `idle` (8 ticks) -> `warning` (2 ticks) -> `erupting` (3 ticks) -> idle
- Eruptions drain 10% battery from agents caught on the tile
- Gas plants built on geysers produce gas during eruptions

**Abandoned structures** spawn within 10 Manhattan distance of the station. Types include:

| Type | Category | Effect |
|------|----------|--------|
| Refinery | Building | Process basalt for +50% bonus quantity |
| Solar Panel Array | Building | Passive charging to nearby rovers |
| Accumulator | Building | Increases base capacity |
| Water Recycler | Building | Converts ice to water (pre-placed at (1,0)) |
| Broken Hauler | Vehicle | Salvageable parts |
| Broken Manipulator | Vehicle | Salvageable parts |

Structures start unexplored. Rovers use `investigate_structure` to reveal and activate them, then `use_refinery` or `upgrade_building` to interact.

### 2.6 Base Upgrades

Rovers at station can purchase upgrades with water and gas:

| Upgrade | Cost | Effect | Max Level |
|---------|------|--------|-----------|
| `charge_mk2` | 50 water, 20 gas | Double station charge rate | 1 |
| `extended_fuel` | 30 water, 10 gas | +100 fuel capacity for all rovers | 2 |
| `enhanced_scanner` | 20 water, 15 gas | +1 rover reveal radius | 2 |
| `repair_bay` | 40 water, 30 gas | Auto-repair rovers to full battery at station | 1 |

### 2.7 World State Structure

```json
{
  "tick": 42,
  "agents": {
    "rover-mistral": {
      "position": [3, 5], "battery": 0.78, "inventory": [],
      "goal_confidence": 0.65, "model": "mistral-small-latest"
    },
    "drone-mistral": { "position": [8, -2], "battery": 0.65 },
    "hauler-mistral": { "position": [1, 1], "battery": 0.90, "inventory": [] },
    "station": { "position": [0, 0] }
  },
  "revealed_tiles": { "(3,5)": { "terrain": "sand", "vein": null } },
  "stones": [
    { "position": [4, 6], "type": "unknown", "grade": "unknown", "analyzed": false }
  ],
  "ice_deposits": [
    { "position": [5, 3], "quantity": 40, "gathered": false }
  ],
  "obstacles": [
    { "position": [7, 2], "kind": "mountain", "state": "idle" },
    { "position": [9, -1], "kind": "geyser", "state": "warning" }
  ],
  "structures": [
    { "type": "refinery", "position": [-3, 2], "explored": false, "active": false }
  ],
  "gas_plants": [],
  "ground_items": [],
  "storm": { "phase": "clear", "intensity": 0.0, "next_storm_tick": 65 },
  "mission": {
    "status": "running", "target_quantity": 300,
    "collected_quantity": 0
  },
  "station_resources": { "water": 0, "gas": 0, "basalt_delivered": 0 },
  "power_budgets": {},
  "emergency_mode": false,
  "upgrades": {}
}
```

---

## 3. Agents and Tools

### 3.1 Rover (`rover-mistral`)

Primary ground agent. Moves across the surface, analyzes and digs veins, manages resources, communicates with peers, and requests human confirmation for high-risk actions.

| Tool | Description | Cost |
|------|-------------|------|
| `move` | Move 1-3 tiles in a cardinal direction | 1 fuel/tile |
| `analyze` | Reveal true grade/type of vein at position | 3 fuel |
| `dig` | Extract analyzed vein into inventory | 6 fuel |
| `deploy_solar_panel` | Deploy emergency solar panel at position | 1 fuel |
| `use_solar_battery` | Consume deployed solar panel for battery (+25%) | - |
| `notify` | Send message to station | 2 fuel |
| `notify_peer` | Send direct message to another rover | 2 fuel |
| `gather_ice` | Gather ice deposit at current tile | 4 fuel |
| `harvest_ice` | Harvest ice from deposit near mountains | 4 fuel |
| `recycle_ice` | Convert all ice in inventory to water (at station) | 3 fuel |
| `build_gas_plant` | Build gas plant on adjacent geyser (requires 5 water) | 8 fuel |
| `collect_gas` | Collect stored gas from adjacent gas plant | 2 fuel |
| `upgrade_base` | Purchase station upgrade with water/gas (at station) | 5 fuel |
| `investigate_structure` | Investigate adjacent abandoned structure | 2 fuel |
| `use_refinery` | Process basalt at active refinery (+50% quantity) | 5 fuel |
| `upgrade_building` | Upgrade adjacent active building | battery + basalt |
| `drop_item` | Drop inventory item for haulers to collect | - |
| `request_confirm` | Request human confirmation for high-risk action | - |

- Fuel capacity: 350 units (extendable via `extended_fuel` upgrade)
- Battery stored as 0.0 to 1.0 fraction
- Inventory: max 3 veins carried at once
- Solar panels: 0.25 capacity each, max 2 deployed
- Multiple rover models: `rover-mistral` (small), `rover-large`, `rover-medium`, `rover-codestral`, `rover-ministral`, `rover-magistral`, `rover-2` (HuggingFace Qwen3-32B)

### 3.2 Drone (`drone-mistral`)

Aerial scout. Covers large areas quickly with wider visibility. Scans return concentration readings indicating proximity to high-grade veins.

| Tool | Description | Cost |
|------|-------------|------|
| `move` | Fly 1-6 tiles in a cardinal direction | 3 fuel/tile |
| `scan` | Area scan returning concentration probabilities for surrounding tiles (radius 6) | 2 fuel |
| `notify` | Send message to station | 2 fuel |

- Fuel capacity: 250 units
- Reveal radius: 6 tiles
- Unaffected by storm move failures (airborne)

### 3.3 Hauler (`hauler-mistral`)

Heavy transport vehicle. Collects cargo from rovers or the ground and delivers to station. Slower than rovers but larger inventory.

| Tool | Description | Cost |
|------|-------------|------|
| `move` | Move 1-2 tiles in a cardinal direction | 1 fuel/tile |
| `load_cargo` | Pick up items at current position (ice, dropped items) | 2 fuel |
| `unload_cargo` | Unload all cargo (at station: delivered to storage) | 1 fuel |
| `notify` | Send message to station | 2 fuel |

- Fuel capacity: 400 units
- Inventory: max 8 items
- Reveal radius: 2 tiles

### 3.4 Station (`station`)

Fixed at position `(0, 0)`. Manages power, charges agents, assigns missions, recalls agents, and allocates power budgets.

| Tool | Description |
|------|-------------|
| `assign_mission` | Assign a mission objective to an agent |
| `broadcast_alert` | Broadcast alert message to all agents |
| `charge_agent` | Recharge co-located agent battery (+20% per call) |
| `recall_agent` | Issue emergency recall command to an agent |
| `allocate_power` | Set minimum battery threshold for an agent |

**Power Management**: The station can set per-agent power budgets via `allocate_power(agent_id, amount)`. When an agent's battery drops below its allocated threshold, a `PowerBudgetWarning` event fires (with 3-tick debounce). When total power demand exceeds `STATION_POWER_CAPACITY` (1.0), `EmergencyModeActivated` fires.

---

## 4. Mission System

### 4.1 Primary Mission

Collect 300 units of basalt and deliver to station at `(0, 0)`.

### 4.2 Mission Flow

1. Station assigns mission to all field agents (rovers, drones, haulers)
2. Drones scout terrain, scanning for vein concentration readings
3. Rovers move to veins, analyze them, dig high-grade samples
4. Rovers carry samples back to station (max 3 per trip) or drop for haulers
5. Haulers collect from rovers and deliver to station (max 8 per trip)
6. Station charges agents when they return with low battery
7. Rovers gather ice, recycle to water, build gas plants, purchase upgrades
8. Repeat until 300 units collected

### 4.3 Probabilistic Goal Structure

```json
{
  "goal_id": "G-01",
  "description": "Collect basalt samples",
  "confidence": 0.0,
  "threshold": 0.9
}
```

`confidence` updates dynamically as agents act:

| Event | Confidence Change |
|-------|-------------------|
| Successful action | +0.05 |
| Failed action | -0.05 |
| Fallback/hazard | -0.08 |
| Delivery to station | +0.10 |
| Mission reassignment | Reset to 0.5 |

Confidence is clamped to `[0.0, 1.0]`. Goal is satisfied when `confidence >= threshold`. Each agent tracks its own `goal_confidence` in its state, exposed in observation contexts for LLM introspection.

The UI displays a color-coded confidence bar per agent:
- Green: >= 70%
- Amber: >= 40%
- Red: < 40%

---

## 5. Agent Loop

Each tick, every agent runs this cycle via `BaseAgent.tick()`:

### 5.1 Observe

Read world state slice: position, battery level, nearby revealed tiles, visible stones, ice deposits, structures, obstacles, storm info, pending commands, unread messages, other agent positions, goal confidence.

### 5.2 Reason (LLM)

LLM API call with the agent's system prompt, current observations, and available tools. The LLM evaluates state and proposes an action via tool call.

Structured reasoning prefix enforces format:
```
SITUATION: <state> | OPTIONS: <a, b> | DECISION: <choice + why> | RISK: low/medium/high
```

Task self-assignment: agents set their own task via `---TASK---` separator in their text response. No Python code computes tasks or injects strategic directives.

### 5.3 Execute

Tool call result mutates world state. Move updates position. Dig adds vein to inventory. Analyze reveals grade. Battery cost applied with storm multiplier if active.

### 5.4 Update Confidence

`goal_confidence` updated based on action outcome (+0.05 success, -0.05 failure, +0.10 delivery, -0.08 fallback/hazard).

### 5.5 Record

- Memory updated (max 8 entries, FIFO)
- Events broadcast to all connected WebSocket clients via Broadcaster
- Training data logged to SurrealDB (turn record with context, action, result, battery delta, position delta, goal confidence before/after)
- Narrator fed with significant events

---

## 6. Storm System

Mars dust storms follow a periodic lifecycle:

### 6.1 Storm Lifecycle

```
clear -> (scheduled delay: 30-80 ticks) -> warning (5 ticks) -> active (10-30 ticks) -> clear
```

| Phase | Duration | Effects |
|-------|----------|---------|
| `clear` | 30-80 ticks between storms | Normal operations |
| `warning` | 5 ticks | `storm_warning` event broadcast |
| `active` | 10-30 ticks | Battery drain multiplier, move failures, visibility reduction |

### 6.2 Storm Effects

During active storms, intensity ramps up to peak at midpoint, then tapers down:

| Effect | Formula |
|--------|---------|
| Battery cost multiplier | `1.0 + 1.5 * intensity` (max 2.5x) |
| Move failure chance | `15% * intensity` (rovers only, drones unaffected) |
| Visibility reduction | 40% |

Storm events: `storm_warning`, `storm_started`, `storm_ended`.

### 6.3 Storm Info in Agent Context

Agents receive storm info in their observation context:
```json
{
  "phase": "active",
  "intensity": 0.75,
  "battery_multiplier": 2.13,
  "move_fail_chance": 0.113
}
```

---

## 7. AI Narration

Dual-narrator dialogue system providing live commentary on simulation events.

### 7.1 Narrators

- **Commander Rex**: Seasoned mission veteran. Pragmatic, dry humor. Think Jeff Goldblum narrating Mars.
- **Dr. Nova**: Planetary scientist. Curious, witty, excited about every rock. Think a fun science podcaster with a PhD.

### 7.2 Pipeline

1. **Event filtering**: Events scored by dramatic weight (1-3). Low-interest events (routine moves, noisy thinking) filtered out.
2. **Event batching**: Events buffered and processed at configurable intervals (default 5s).
3. **Text generation**: Mistral LLM generates 2-4 lines of alternating dialogue with audio emotion tags (`[laughs]`, `[sighs]`, `[whispers]`, `[gasps]`, `[clears throat]`).
4. **Voice synthesis**: ElevenLabs Text-to-Dialogue API converts dialogue to MP3 with per-speaker voice IDs.
5. **Streaming delivery**: Text chunks streamed via `narration_chunk` WebSocket events; final audio delivered as base64 MP3 in `narration` event.

### 7.3 Fallbacks

- If ElevenLabs API key not set: text-only narration (no audio)
- If streaming LLM fails: falls back to non-streaming call
- If dialogue parsing fails: single-narrator fallback
- HuggingFace provider supported as alternative LLM backend

---

## 8. Human-in-the-Loop

### 8.1 Confirmation System

Rovers can request human confirmation before high-risk actions via `request_confirm`:

1. Rover calls `request_confirm(question, timeout)` — loop pauses
2. Host creates pending confirmation, broadcasts `confirm_request` event to UI
3. UI shows `ConfirmModal` with agent context, countdown timer, Confirm/Deny buttons
4. Human responds via `POST /api/confirm` with `{request_id, confirmed}`
5. Host resolves confirmation, unblocks rover loop
6. If timeout (default 30s, max 120s): auto-denies

One pending confirmation per agent. Recommended use: storm zones, hazard tiles, low battery operations.

### 8.2 Voice Commands

Human operator speaks commands via audio upload:

1. Audio uploaded to `POST /api/voice-command`
2. **Voxtral** (Mistral's voice model) transcribes audio with Mars domain context bias
3. LLM parses transcript into structured command: `{command, params, confidence}`
4. Host routes recognized commands (recall_rover, abort_mission, pause/resume)

Supported commands: `recall_rover`, `abort_mission`, `pause_simulation`, `resume_simulation`, `reset_simulation`, `toggle_narration`, `general_message`.

### 8.3 Simulation Controls

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/simulation/pause` | POST | Pause all agent loops |
| `/simulation/resume` | POST | Resume agent loops |
| `/simulation/reset` | POST | Reset world, re-register agents, restart |
| `/simulation/status` | GET | Check pause state |
| `/mission/abort` | POST | Abort current mission |
| `/rover/{rover_id}/recall` | POST | Recall specific rover to station |

---

## 9. Peer Messaging

Rovers communicate directly with other rovers via `notify_peer(target_id, message)`:

- Costs 2 fuel units (same as `notify`)
- Messages delivered through the existing `send_agent_message()` infrastructure
- Target must be a valid active rover ID
- Receiving rover sees unread messages in its observation context
- UI shows magenta communication lines on the world map for `peer_message` events

Use cases: share vein discoveries, warn about hazards, coordinate exploration sectors.

---

## 10. Training Data Pipeline

### 10.1 SurrealDB Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `training_session` | One simulation run | started_at, status, config, result, duration_seconds |
| `training_turn` | Agent decision cycle | session_id, tick, agent_id, context, action_name, action_result, battery_before/after, goal_confidence_before/after |
| `training_event` | Significant events | session_id, tick, source, event_name, payload |
| `training_world_snapshot` | Periodic world state | session_id, tick, world_state |

### 10.2 TrainingLogger

Singleton (`training_logger`) that records data when `TRAINING_DATA_ENABLED=true`:

- `start_session(config)` — creates session record
- `log_turn(turn)` — records each agent decision cycle
- `log_event(event)` — records significant world events
- `log_world_snapshot(tick, state)` — periodic full state captures (configurable interval)
- `end_session(result)` — finalizes session

### 10.3 JSONL Export

`export_session_jsonl(session_id)` produces training-ready records:
```json
{
  "messages": [
    {"role": "system", "content": "<agent context>"},
    {"role": "user", "content": "Observe your surroundings and decide your next move."},
    {"role": "assistant", "content": "<thinking>", "tool_calls": [{"function": {"name": "move", "arguments": "{...}"}}]},
    {"role": "tool", "content": "<result>"}
  ],
  "meta": {"session_id": "...", "tick": 42, "agent_id": "rover-mistral", "action_ok": true}
}
```

### 10.4 Fine-Tuning Integration

The `FineTuningManager` handles Mistral fine-tuning jobs:
- Upload training data files
- Create/list/cancel fine-tuning jobs
- Activate fine-tuned models for agent reasoning or narration

---

## 11. Event System

### 11.1 Event Categories

| Category | Examples |
|----------|---------|
| Agent | BatteryLow, VeinDiscovered, DigSuccess, peer_message |
| Mission | MissionAssigned, DeliveryComplete, mission_success, mission_failed |
| World | ChunkGenerated, BoundsExpanded |
| Storm | storm_warning, storm_started, storm_ended |
| Station | charge_agent, recall, PowerBudgetWarning, EmergencyModeActivated |
| Human | confirm_request, confirm_response, voice_command |
| Narration | narration, narration_chunk |

### 11.2 Agent-to-Agent Communication

- `notify`: Agent sends message to station via Coordinator
- `notify_peer`: Rover sends direct message to another rover
- Messages routed through Host; agents never call each other directly

### 11.3 Power Budget Events

- `PowerBudgetWarning`: Agent battery below allocated threshold (3-tick debounce)
- `EmergencyModeActivated`: Total power demand exceeds station capacity
- `EmergencyModeDeactivated`: Power situation resolved

---

## 12. Message Protocol

```json
{
  "id": "uuid",
  "ts": 1738472912,
  "source": "rover|drone|hauler|station|base|human|world|narrator",
  "type": "event|action|command|tool|stream|narration",
  "name": "EventOrActionName",
  "payload": {},
  "correlation_id": "optional"
}
```

- Host routes messages declaratively
- Agents subscribe to relevant events only
- All messages broadcast to UI via WebSocket

---

## 13. Configuration

All settings managed via `pydantic-settings` (`Settings` class in `config.py`), reading from environment variables or `.env` file.

| Setting | Default | Description |
|---------|---------|-------------|
| `env` | `dev` | Environment name |
| `server_port` | `4009` | Server port |
| `surreal_port` | `4002` | SurrealDB port |
| `surreal_url` | `ws://localhost:4002/rpc` | SurrealDB connection URL |
| `mistral_api_key` | (required) | Mistral AI API key |
| `agent_backend` | `chat_completions` | LLM backend: `chat_completions` or `agents_api` |
| `agents_api_persist_threads` | `true` | Persist Agents API conversation threads across turns |
| `llm_provider` | `mistral` | LLM provider: `mistral` or `huggingface` |
| `agent_turn_interval_seconds` | `0.5` | Base agent tick interval |
| `llm_turn_interval_seconds` | `4.0` | LLM rover turn interval |
| `drone_turn_interval_seconds` | `3.5` | Drone turn interval |
| `hauler_turn_interval_seconds` | `5.0` | Hauler turn interval |
| `world_seed` | (random) | Deterministic world generation seed |
| `active_agents` | (all agents) | Comma-separated list of active agent IDs |
| `elevenlabs_api_key` | (optional) | ElevenLabs API key for voice narration |
| `narration_enabled` | `true` | Enable/disable narration |
| `narration_model` | `mistral-medium-latest` | LLM model for narration text |
| `narration_min_interval_seconds` | `5.0` | Minimum seconds between narrations |
| `voice_transcription_model` | `voxtral-mini-latest` | Model for voice-to-text |
| `voice_command_model` | `mistral-small-latest` | LLM for parsing voice transcripts |
| `training_data_enabled` | `false` | Enable training data logging |
| `training_data_dir` | `./training_data` | Directory for training data files |
| `training_snapshot_interval` | `10` | Ticks between world snapshots |
| `fine_tuned_agent_model` | (none) | Fine-tuned model for agent reasoning |
| `fine_tuned_narration_model` | (none) | Fine-tuned model for narration |

---

## 14. API Endpoints

### 14.1 Simulation Control

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/simulation/pause` | Pause simulation |
| POST | `/simulation/resume` | Resume simulation |
| GET | `/simulation/status` | Get pause state |
| POST | `/simulation/reset` | Reset and restart simulation |
| POST | `/mission/abort` | Abort current mission |
| POST | `/rover/{rover_id}/recall` | Recall a rover to station |
| POST | `/api/confirm` | Respond to human confirmation request |

### 14.2 Narration and Voice

| Method | Path | Description |
|--------|------|-------------|
| POST | `/narration/toggle` | Toggle narration on/off |
| GET | `/narration/status` | Get narration enabled state |
| POST | `/api/voice-command` | Upload audio for voice command processing |

### 14.3 Training Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/training/sessions` | List training sessions |
| GET | `/api/training/sessions/{id}` | Get session with stats |
| GET | `/api/training/sessions/{id}/turns` | Get turns for session |
| GET | `/api/training/sessions/{id}/events` | Get events for session |
| GET | `/api/training/sessions/{id}/snapshots` | Get world snapshots |
| GET | `/api/training/sessions/{id}/export` | Export as JSONL for fine-tuning |

### 14.4 Fine-Tuning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/fine-tuning/status` | Fine-tuning configuration status |
| GET | `/fine-tuning/data` | Training data file stats |
| POST | `/fine-tuning/jobs` | Create fine-tuning job |
| GET | `/fine-tuning/jobs` | List fine-tuning jobs |
| GET | `/fine-tuning/jobs/{id}` | Get job details |
| DELETE | `/fine-tuning/jobs/{id}` | Cancel job |
| POST | `/fine-tuning/jobs/{id}/activate` | Activate fine-tuned model |

### 14.5 WebSocket

| Path | Description |
|------|-------------|
| `/ws` | Real-time simulation event stream. Sends initial world state on connect. |

---

## 15. Demo Timeline (5-Minute)

| Time | Event | Agents |
|------|-------|--------|
| 0:00 | Mission assigned: collect 300 basalt units | Station -> All |
| 0:15 | Drone takes off, scans area around origin | drone-mistral |
| 0:30 | Drone discovers veins, narrators comment | drone-mistral |
| 0:45 | Rovers move toward nearest veins, analyze | rover-mistral |
| 1:00 | Rovers dig high-grade basalt, hauler deploys | rover + hauler |
| 1:30 | Drone expands search radius, finds more veins | drone-mistral |
| 2:00 | Storm warning broadcast, rovers assess risk | All |
| 2:30 | Storm active; rovers request confirmation for risky moves | rover + human |
| 3:00 | Station charges agents, rover delivers samples | station + rover |
| 3:30 | Rovers gather ice, recycle to water, build gas plant | rovers |
| 4:00 | Hauler transports cargo, rovers purchase upgrade | hauler + rover |
| 4:30 | Second exploration run, peers share discoveries | rover-to-rover |
| 5:00 | Mission target reached, confidence threshold met | All |

---

## 16. Emergent Simulation Characteristics

- LLM-driven decision making produces non-deterministic, adaptive behavior
- Agents respond to changing conditions: battery constraints force return trips, storms alter strategy, new vein discoveries redirect exploration
- Drone-rover cooperation emerges naturally from shared world state and notify messages
- Peer messaging enables rover-to-rover coordination without station intermediation
- Hauler-rover logistics emerge: rovers focus on exploring while haulers handle transport
- Fog-of-war creates genuine exploration, not just pathfinding on a known map
- Procedural generation means every simulation run produces different terrain
- Storm system adds temporal pressure and risk assessment to decisions
- Resource economy (ice -> water -> upgrades) creates medium-term strategic decisions
- Human-in-the-loop confirmation adds safety for high-risk autonomous actions
- Dual-narrator commentary makes the simulation watchable and engaging
- Training data pipeline enables fine-tuning agents on their own successful runs
