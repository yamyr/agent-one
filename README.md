# Agent One — Multi-Agent Mars Mission Simulation

A multi-agent LLM-powered simulation where autonomous agents collaborate to complete Mars surface missions. Built with Mistral AI for the Mistral Hackathon (Feb 28 – Mar 1).

## Concept

Autonomous agents — a **Rover**, **Drone**, and **Station** — coordinate through a central **Coordinator** to carry out Mars exploration missions. Each agent runs its own LLM reasoning loop, observes the world state, executes tool calls, and communicates via a structured message protocol. Goals are tracked probabilistically, and a human operator can intervene at any time.

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
  │ MoveTo  │   │  Scan    │   │ Allocate │
  │ Drill   │   │  Map     │   │  Power   │
  │ Carry   │   │  Relay   │   │  Alert   │
  └─────────┘   └──────────┘   └──────────┘
```

## How It Works

Each simulation tick follows this loop per agent:

1. **Observe** — Read a slice of the world state (zones, hazards, battery, storms)
2. **Evaluate** — LLM interprets state, proposes tasks, assesses goal health
3. **Execute** — Tool calls mutate the world; progress is streamed
4. **Update Confidence** — Goal probability (0.0–1.0) adjusts based on results
5. **Emit Actions** — Notify other agents/base of events (`SafeRouteIdentified`, `PowerBudgetWarning`, `StormApproaching`, etc.)

Agents never communicate directly — all messages route through the Coordinator.

## Tech Stack

- **Python 3.12+**
- **Mistral AI** (`mistralai` SDK)
- **JSON stdio** for agent subprocess communication

## Setup

```bash
# Clone
git clone https://github.com/mhack-agent-one/agent-one.git
cd agent-one

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install mistralai

# API key
export MISTRAL_API_KEY="your-key-here"
```

## Project Structure

```
agent-one/
├── SPEC.md           # Full system specification
├── IDEA.md           # High-level vision
├── ROADMAP.md        # Development milestones
├── CLAUDE.md         # Developer guidance
└── hackathon_info.md # Event details
```

## Key Concepts

### World Model

A Python dict representing the Mars environment: zones with hazards, rock types (core, basalt), agent positions, battery/power levels, storm intensity, visibility, and temperature.

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

## Roadmap

| Milestone | Description |
|-----------|-------------|
| **0** | Scaffold — project structure, base agent class, protocol types |
| **1** | Coordinator + Rover — world model, agent spawning, rover tools |
| **2** | Drone + Communication — scanning, probabilistic mapping, action routing |
| **3** | Events + Human-in-the-loop — storms, terrain shifts, operator confirmations |
| **4** | Station + Goal Tracking — power management, confidence visualization |
| **5** | Demo Polish — scripted timeline, UI, dry runs |

## License

See repository for license details.
