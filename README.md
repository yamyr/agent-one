# Agent One — Multi-Agent Mars Mission Simulation

A multi-agent LLM-powered simulation where autonomous agents collaborate to complete Mars surface missions. Built with Mistral AI for the Mistral Hackathon (Feb 28 -- Mar 1).

## Concept

Autonomous agents -- **Rovers**, a **Drone**, a **Hauler**, and a **Station** -- coordinate through a central **Host** to carry out Mars exploration missions. Each agent runs its own LLM reasoning loop (Mistral API), observes the world state, executes tool calls, and communicates via a structured message protocol. Goals are tracked probabilistically, and a human operator can intervene via UI controls, confirmation prompts, or voice commands.

```
                      +---------------------+
                      |    Base / Control    |  <- Human: voice commands, confirm prompts, controls
                      +----------+----------+
                                 |
                +----------------+----------------+
                |           HOST                  |
                |  Routes messages - Manages      |
                |  lifecycle - Confirmations       |
                +--+-------+-------+-------+------+
                   |       |       |       |
              +----+  +---+--+ +--+---+ +-+------+
              |Rover|  |Drone | |Hauler| |Station |
              | Dig |  | Scan | | Load | |Charge  |
              | Ice |  | Map  | |Unload| |Mission |
              |Peer |  |Notify| |Deliver|Recall  |
              |Confirm|       |       | |Power   |
              +------+ +------+ +------+ +--------+
                                    |
               +--------------------+--------------------+
               |                                         |
        +------+-------+                          +------+------+
        |   Narrator   |                          |  Training   |
        | Rex + Nova   |                          |  Pipeline   |
        | Mistral LLM  |                          |  SurrealDB  |
        | ElevenLabs   |                          |  JSONL      |
        +--------------+                          +-------------+
```

### Key Features

- **Grid-based Mars world** with terrain, hidden vein types, fog-of-war visibility, procedural generation, and concentration maps
- **Resource economy** -- basalt (primary mission), ice -> water, geysers -> gas, all used for base upgrades
- **AI Narration** -- Dual-narrator dialogue (Commander Rex + Dr. Nova) via Mistral LLM, with ElevenLabs TTS voice synthesis and audio emotion tags
- **Storm system** -- Periodic dust storms with battery drain multipliers, move failure chance, and visibility reduction
- **Human-in-the-loop** -- Confirmation prompts for high-risk actions, voice commands via Voxtral transcription
- **Peer messaging** -- Rover-to-rover direct communication for coordination
- **Goal confidence tracking** -- Per-agent confidence (0.0-1.0) with color-coded UI bars
- **Multiple LLM backends** -- Chat Completions (default) and Agents API with persistent conversation threads
- **Training data pipeline** -- SurrealDB logging of every agent turn, JSONL export for Mistral fine-tuning
- **Base upgrades** -- Spend water and gas to improve charge speed, fuel capacity, scanner range, or auto-repair
- **Hauler agent** -- Heavy transport vehicle that collects cargo from rovers, freeing them to keep exploring
- **Real-time UI** -- Vue 3 mission control dashboard with surface map, rover telemetry, event log, narration player, and confidence bars via WebSocket streaming
- **Voice command** -- Speak to the simulation (recall, abort, pause). Voxtral transcription + LLM command parsing
- **GitHub -> Discord notifications** -- PR and main-branch push events forwarded to Discord via webhook

## How It Works

Each simulation tick follows this loop per agent:

1. **Observe** -- Read a slice of the world state (position, battery, stones, ice, obstacles, storms, messages)
2. **Reason (LLM)** -- Mistral API call with system prompt, observations, and tool definitions
3. **Execute** -- Tool calls mutate the world; progress is streamed
4. **Update Confidence** -- Goal probability (0.0-1.0) adjusts based on results
5. **Record** -- Training data logged to SurrealDB; events broadcast to UI and narrator

Agents never communicate directly -- all messages route through the Host.

## Tech Stack

- **Backend**: Python 3.14+, FastAPI, SurrealDB, `mistralai` SDK, `elevenlabs` SDK, `uv` package manager
- **Frontend**: Vue 3 (Composition API), Vite 7, Node 24 LTS
- **CI/CD**: GitHub Actions (lint, test, build, coverage), Discord webhook notifications
- **Deployment**: Docker multi-stage build, Railway

## Setup

```bash
# Clone
git clone https://github.com/yamyr/agent-one.git
cd agent-one

# Server
cd server
uv sync                        # install Python deps
export MISTRAL_API_KEY="your-key-here"
export ELEVENLABS_API_KEY="your-key-here"  # optional -- enables voice narration
./run                          # uvicorn on :4009 with --reload

# UI (separate terminal)
cd ui
npm install
npm run dev                    # vite on :4089
```

## Project Structure

```
agent-one/
+-- server/                        # Python FastAPI backend (port 4009)
|   +-- app/
|   |   +-- main.py                # FastAPI app, lifespan, CORS, agent registration
|   |   +-- config.py              # pydantic-settings, reads .env
|   |   +-- host.py                # Host message router, agent lifecycle, confirmations
|   |   +-- base_agent.py          # BaseAgent ABC with self-running tick loop
|   |   +-- agent.py               # Rover/Drone/Hauler reasoners + loop classes
|   |   +-- agents_api.py          # Agents API backend (beta) reasoners
|   |   +-- station.py             # Station agent logic (charge, mission, recall, power)
|   |   +-- world.py               # World model, simulation tick loop, resource economy
|   |   +-- storm.py               # Dust storm system (lifecycle, effects)
|   |   +-- narrator.py            # Dual-narrator engine (Mistral + ElevenLabs TTS)
|   |   +-- voice.py               # Voice command processor (Voxtral + LLM parsing)
|   |   +-- models.py              # Pydantic context models (RoverContext, StationContext, etc.)
|   |   +-- protocol.py            # Message protocol helpers
|   |   +-- broadcast.py           # WebSocket fan-out singleton
|   |   +-- training_logger.py     # SurrealDB training data persistence
|   |   +-- training_models.py     # Pydantic models for training records
|   |   +-- training.py            # Training data collector (file-based)
|   |   +-- finetuning.py          # Mistral fine-tuning job manager
|   |   +-- views.py               # REST endpoints + /ws WebSocket
|   |   +-- db.py                  # SurrealDB connection helpers
|   +-- tests/
+-- ui/                            # Vue 3 + Vite frontend (port 4089)
|   +-- src/components/
|       +-- WorldMap.vue            # SVG grid map with fog-of-war, comm lines
|       +-- NarrationPlayer.vue     # AI narration with typewriter + audio
|       +-- ConfirmModal.vue        # Human confirmation overlay
|       +-- ConfidenceBar.vue       # Goal confidence bar (color-coded)
|       +-- PowerBudgetBar.vue      # Power budget indicator
|       +-- EventLog.vue            # Scrolling event log
|       +-- AgentPane.vue           # Individual agent telemetry
|       +-- AgentPanes.vue          # Agent panel container
|       +-- AgentDetailModal.vue    # Agent detail overlay
|       +-- MissionBar.vue          # Mission progress bar
|       +-- AppHeader.vue           # App header
+-- .github/workflows/
|   +-- ci.yml                     # Lint, test, build, coverage CI pipeline
|   +-- discord-git-notify.yml     # GitHub -> Discord notifications
+-- specs/                         # Feature specifications
+-- SPEC.md                        # Full system specification
+-- CLAUDE.md                      # Developer guidance
+-- Changelog.md                   # Project changelog
+-- Dockerfile                     # Multi-stage Docker build
```

## Agents

### Rover

Ground exploration agent. Moves across the surface, analyzes and digs basalt veins, gathers ice, builds gas plants, purchases upgrades, communicates with peers, and requests human confirmation for high-risk actions.

**Tools**: `move`, `analyze`, `dig`, `deploy_solar_panel`, `use_solar_battery`, `notify`, `notify_peer`, `gather_ice`, `harvest_ice`, `recycle_ice`, `build_gas_plant`, `collect_gas`, `upgrade_base`, `investigate_structure`, `use_refinery`, `upgrade_building`, `drop_item`, `request_confirm`

Multiple models available: `rover-mistral`, `rover-large`, `rover-medium`, `rover-codestral`, `rover-ministral`, `rover-magistral`, `rover-2` (HuggingFace).

### Drone

Aerial scout with wide visibility. Scans terrain for vein concentration readings and reports to station.

**Tools**: `move`, `scan`, `notify`

### Hauler

Heavy transport vehicle. Picks up cargo from rovers or the ground and delivers to station.

**Tools**: `move`, `load_cargo`, `unload_cargo`, `notify`

### Station

Fixed at origin (0,0). Manages missions, charges agents, recalls agents, and allocates power budgets.

**Tools**: `assign_mission`, `broadcast_alert`, `charge_agent`, `recall_agent`, `allocate_power`

## Key Concepts

### World Model

A Python dict representing the Mars environment: infinite chunk-based grid with fog-of-war, basalt veins, ice deposits, gas geysers, abandoned structures, obstacles (mountains), agent positions, battery/power levels, storm state, resource storage, and simulation tick state.

### Resource Economy

- **Basalt**: Primary mission resource. Dug from analyzed veins, delivered to station.
- **Ice**: Gathered near mountains. Recycled at station into water (2:1 ratio).
- **Water**: Used for gas plant construction and base upgrades.
- **Gas**: Produced by gas plants on geysers. Used for base upgrades.

### Storm System

Periodic dust storms cycle through clear -> warning -> active -> clear. Active storms increase battery drain (up to 2.5x), cause probabilistic rover move failures (up to 15%), and reduce visibility.

### Probabilistic Goals

```json
{
  "goal_id": "G-01",
  "description": "Collect basalt samples",
  "confidence": 0.65,
  "threshold": 0.9
}
```

A goal is satisfied when `confidence >= threshold`. Confidence updates dynamically as agents act and the world changes: +0.05 on success, -0.05 on failure, +0.10 on delivery, -0.08 on fallback/hazard.

### Message Protocol

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | Yes | Mistral AI API key for LLM agent reasoning and narration |
| `ELEVENLABS_API_KEY` | No | ElevenLabs API key for voice narration (text narration works without it) |
| `AGENT_BACKEND` | No | LLM backend: `chat_completions` (default) or `agents_api` |
| `AGENTS_API_PERSIST_THREADS` | No | Persist Agents API conversations across turns (default: true) |
| `LLM_PROVIDER` | No | LLM provider: `mistral` (default) or `huggingface` |
| `NARRATION_ENABLED` | No | Enable/disable narration at startup (default: true) |
| `NARRATION_MODEL` | No | LLM model for narration (default: `mistral-medium-latest`) |
| `NARRATION_VOICE_ID_MALE` | No | ElevenLabs voice ID for Commander Rex |
| `NARRATION_VOICE_ID_FEMALE` | No | ElevenLabs voice ID for Dr. Nova |
| `NARRATION_MIN_INTERVAL_SECONDS` | No | Minimum seconds between narrations (default: 5) |
| `VOICE_TRANSCRIPTION_MODEL` | No | Model for voice-to-text (default: `voxtral-mini-latest`) |
| `VOICE_COMMAND_MODEL` | No | LLM for parsing voice transcripts (default: `mistral-small-latest`) |
| `TRAINING_DATA_ENABLED` | No | Enable training data logging to SurrealDB (default: false) |
| `TRAINING_DATA_DIR` | No | Directory for training data files (default: `./training_data`) |
| `TRAINING_SNAPSHOT_INTERVAL` | No | Ticks between world state snapshots (default: 10) |
| `FINE_TUNED_AGENT_MODEL` | No | Fine-tuned model override for agent reasoning |
| `FINE_TUNED_NARRATION_MODEL` | No | Fine-tuned model override for narration |
| `WORLD_SEED` | No | Deterministic world generation seed |
| `ACTIVE_AGENTS` | No | Comma-separated list of agent IDs to activate |
| `LLM_TURN_INTERVAL_SECONDS` | No | Rover turn interval in seconds (default: 4.0) |
| `DRONE_TURN_INTERVAL_SECONDS` | No | Drone turn interval (default: 3.5) |
| `HAULER_TURN_INTERVAL_SECONDS` | No | Hauler turn interval (default: 5.0) |

### Discord Notifications (GitHub Secrets)

| Secret | Required | Description |
|--------|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Yes | Default Discord webhook (fallback for both channels) |
| `DISCORD_WEBHOOK_URL_PR` | No | Optional separate webhook for PR notifications |
| `DISCORD_WEBHOOK_URL_MAIN` | No | Optional separate webhook for main-branch push notifications |

## API Endpoints

### Simulation Control

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/simulation/pause` | Pause simulation |
| POST | `/simulation/resume` | Resume simulation |
| GET | `/simulation/status` | Get pause state |
| POST | `/simulation/reset` | Reset and restart |
| POST | `/mission/abort` | Abort current mission |
| POST | `/rover/{id}/recall` | Recall a rover |
| POST | `/api/confirm` | Respond to confirmation prompt |
| POST | `/api/voice-command` | Voice command (audio upload) |

### Narration

| Method | Path | Description |
|--------|------|-------------|
| POST | `/narration/toggle` | Toggle narration |
| GET | `/narration/status` | Narration state |

### Training Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/training/sessions` | List sessions |
| GET | `/api/training/sessions/{id}` | Session detail + stats |
| GET | `/api/training/sessions/{id}/turns` | Session turns |
| GET | `/api/training/sessions/{id}/events` | Session events |
| GET | `/api/training/sessions/{id}/export` | JSONL export |

### Fine-Tuning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/fine-tuning/status` | Config status |
| POST | `/fine-tuning/jobs` | Create job |
| GET | `/fine-tuning/jobs` | List jobs |
| POST | `/fine-tuning/jobs/{id}/activate` | Activate model |

### WebSocket

| Path | Description |
|------|-------------|
| `/ws` | Real-time event stream (sends initial state on connect) |

## License

See repository for license details.
