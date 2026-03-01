# Agent One — Multi-Agent Mars Mission Simulation

A multi-agent LLM-powered simulation where autonomous agents collaborate to complete Mars surface missions. Built with Mistral AI for the Mistral Hackathon (Feb 28 – Mar 1).

## Concept

Autonomous agents — a **Rover**, **Drone**, and **Station** — coordinate through a central **Coordinator** to carry out Mars exploration missions. Each agent runs its own LLM reasoning loop (Mistral API), observes the world state, executes tool calls, and communicates via a structured message protocol. Goals are tracked probabilistically, and a human operator can intervene at any time.

```
┌─────────────────────┐
│    Base / Control    │   ← Human operator: assigns missions, approves high-risk tasks
└─────────┬───────────┘
          ▼
┌─────────────────────────────────────────────┐
│              COORDINATOR                     │
│  Spawns agents · Routes messages · Updates   │
│  world state · Manages tool calls · Events   │
└──────┬──────────────┬──────────────┬────────┘
       ▼              ▼              ▼
  ┌─────────┐   ┌──────────┐   ┌──────────┐
  │  Rover  │   │  Drone   │   │ Station  │
  │ Move    │   │  Scan    │   │ Charge   │
  │ Dig     │   │  Map     │   │  Power   │
  │ Analyze │   │  Relay   │   │  Alert   │
  │ Notify  │   │          │   │          │
  └─────────┘   └──────────┘   └──────────┘
```

### Key Features

- **Grid-based Mars world** with terrain, hidden stone types (core/basalt), fog-of-war visibility, and concentration maps
- **AI Narration** — Mistral LLM generates live commentary ("David Attenborough meets space podcaster"), with optional ElevenLabs TTS voice synthesis including emotion tags
- **Real-time UI** — Vue 3 mission control dashboard with surface map, rover telemetry, event log, and narration player via WebSocket streaming
- **Per-rover visibility radius** shown as colored dashed circles on the map
- **Rovers start at station (0,0)** and explore outward autonomously
- **GitHub → Discord notifications** — PR and main-branch push events forwarded to Discord channels via webhook
- **Voice Command** — Speak naturally to the simulation ("Recall all rovers", "Abort mission"). Audio is transcribed via **Voxtral** (Mistral's voice model) and parsed into structured commands by an LLM.

## How It Works

Each simulation tick follows this loop per agent:

1. **Observe** — Read a slice of the world state (zones, hazards, battery, storms)
2. **Evaluate** — LLM interprets state, proposes tasks, assesses goal health
3. **Execute** — Tool calls mutate the world; progress is streamed
4. **Update Confidence** — Goal probability (0.0–1.0) adjusts based on results
5. **Emit Actions** — Notify other agents/base of events (`SafeRouteIdentified`, `PowerBudgetWarning`, `StormApproaching`, etc.)

Agents never communicate directly — all messages route through the Coordinator.

## Tech Stack

- **Backend**: Python 3.14+, FastAPI, SurrealDB, `mistralai` SDK, `elevenlabs` SDK, `uv` package manager
- **Frontend**: Vue 3 (Composition API), Vite 7, Node 24 LTS
- **CI/CD**: GitHub Actions (lint, test, build), Discord webhook notifications
- **Deployment**: Docker multi-stage build, Railway

## Setup

```bash
# Clone
git clone https://github.com/mhack-agent-one/agent-one.git
cd agent-one

# Server
cd server
uv sync                        # install Python deps
export MISTRAL_API_KEY="your-key-here"
export ELEVENLABS_API_KEY="your-key-here"  # optional — enables voice narration
./run                          # uvicorn on :4009 with --reload

# UI (separate terminal)
cd ui
npm install
npm run dev                    # vite on :4089
```

## Project Structure

```
agent-one/
├── server/                        # Python FastAPI backend (port 4009)
│   ├── app/
│   │   ├── main.py                # FastAPI app, lifespan, CORS, agent loop
│   │   ├── config.py              # pydantic-settings, reads .env
│   │   ├── views.py               # REST endpoints + /ws WebSocket
│   │   ├── broadcast.py           # WebSocket fan-out singleton
│   │   ├── agent.py               # RoverAgent (Mistral LLM) + MockRoverAgent
│   │   ├── narrator.py            # AI narration engine (Mistral + ElevenLabs TTS)
│   │   ├── station.py             # Station agent logic
│   │   ├── world.py               # World model + simulation
│   │   └── db.py                  # SurrealDB connection helpers
│   └── tests/
├── ui/                            # Vue 3 + Vite frontend (port 4089)
│   └── src/components/
│       ├── WorldMap.vue            # SVG grid map with fog-of-war
│       ├── NarrationPlayer.vue     # AI narration with typewriter + audio
│       ├── EventLog.vue            # Scrolling event log
│       ├── AgentPane.vue           # Individual agent telemetry
│       ├── AgentPanes.vue          # Agent panel container
│       ├── AgentDetailModal.vue    # Agent detail overlay
│       ├── MissionBar.vue          # Mission progress bar
│       └── AppHeader.vue           # App header
├── .github/workflows/
│   ├── ci.yml                     # Lint, test, build CI pipeline
│   └── discord-git-notify.yml     # GitHub → Discord notifications
├── SPEC.md                        # Full system specification
├── CLAUDE.md                      # Developer guidance
├── Changelog.md                   # Project changelog
└── Dockerfile                     # Multi-stage Docker build
```

## Key Concepts

### World Model

A Python dict representing the Mars environment: infinite chunk-based grid with fog-of-war, basalt veins with grades (low/medium/high/rich/pristine), agent positions, battery/power levels, and simulation tick state.

### Probabilistic Goals

```json
{
  "goal_id": "G-01",
  "description": "Collect core sample from Crater-Alpha",
  "confidence": 0.0,
  "threshold": 0.9
}
```

A goal is satisfied when `confidence >= threshold`. Confidence updates dynamically as agents act and the world changes.

### Message Protocol

```json
{
  "id": "uuid",
  "ts": 1738472912,
  "source": "rover|drone|station|base|human|world",
  "type": "event|action|command|tool|stream",
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
| `NARRATION_ENABLED` | No | Enable/disable narration at startup (default: off) |
| `NARRATION_VOICE_ID` | No | ElevenLabs voice ID for TTS |
| `NARRATION_MIN_INTERVAL_SECONDS` | No | Minimum seconds between narrations |
| `VOICE_TRANSCRIPTION_MODEL` | No | Model for voice-to-text (default: `voxtral-mini-latest`) |
| `VOICE_COMMAND_MODEL` | No | LLM for parsing voice transcripts (default: `mistral-small-latest`) |

### Discord Notifications (GitHub Secrets)

| Secret | Required | Description |
|--------|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Yes | Default Discord webhook (fallback for both channels) |
| `DISCORD_WEBHOOK_URL_PR` | No | Optional separate webhook for PR notifications |
| `DISCORD_WEBHOOK_URL_MAIN` | No | Optional separate webhook for main-branch push notifications |

## License

See repository for license details.
