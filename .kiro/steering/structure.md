# Project Structure

```
agent-one/
├── server/                     # Python FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app, lifespan, CORS, health endpoint, agent loop
│   │   ├── config.py           # pydantic-settings (Settings class, reads .env)
│   │   ├── db.py               # SurrealDB connection helpers, get_db() generator
│   │   ├── views.py            # REST endpoints + /ws WebSocket endpoint
│   │   ├── broadcast.py        # Broadcaster singleton for WebSocket fan-out
│   │   ├── agent.py            # RoverAgent (Mistral LLM) + MockRoverAgent (fallback)
│   │   ├── narrator.py         # AI narration: Mistral text + ElevenLabs TTS, streaming chunks
│   │   ├── station.py          # Station agent logic (charge rovers, mission assignment)
│   │   ├── world.py            # World model, simulation tick loop, task planning
│   │   └── sim/                # Deterministic simulation engine
│   │       ├── models.py       # Domain models: WorldState, RoverState, StationState, GridState, etc.
│   │       ├── engine.py       # SimulationEngine: validates actions, advances world state
│   │       ├── world_factory.py# WorldFactory: seeded world creation with guaranteed feasibility
│   │       └── errors.py       # Error constants (INVALID_OUT_OF_BOUNDS, etc.)
│   ├── tests/
│   │   ├── conftest.py         # In-memory SurrealDB setup, CaseWithDB base class
│   │   ├── test_sim_engine.py  # SimulationEngine unit tests
│   │   ├── test_narrator.py    # Narrator unit tests
│   │   ├── test_station.py     # Station agent tests
│   │   └── ...                 # Other test modules
│   ├── pyproject.toml          # Python project config (uv, ruff)
│   ├── uv.lock                 # Locked dependencies
│   └── run                     # Dev server start script
├── ui/                         # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── App.vue             # Root component, WebSocket connection, layout
│   │   ├── main.js             # Vue app entry point
│   │   └── components/
│   │       ├── WorldMap.vue    # SVG grid map with fog-of-war, visibility radius circles
│   │       ├── NarrationPlayer.vue # AI narration display with typewriter effect + audio playback
│   │       ├── EventLog.vue    # Scrolling event log (below map)
│   │       ├── AgentPane.vue   # Individual agent telemetry card
│   │       ├── AgentPanes.vue  # Agent panel container
│   │       ├── AgentDetailModal.vue # Agent detail overlay
│   │       ├── MissionBar.vue  # Mission progress bar
│   │       └── AppHeader.vue   # App header
│   ├── vite.config.js          # Vite config with proxy to backend
│   └── package.json
├── .github/workflows/
│   ├── ci.yml                  # Lint (ruff + eslint), test (rut + SurrealDB), build, Docker verify
│   └── discord-git-notify.yml  # GitHub → Discord webhook notifications (PR + main push)
├── Dockerfile                  # Multi-stage: Node build → Python runtime
├── railway.toml                # Railway deployment config
├── SPEC.md                     # Full system specification
├── CLAUDE.md                   # Developer guidance
├── Changelog.md                # Project changelog
└── tasks/                      # Task tracking plans
```

## Key Architecture Patterns

- The simulation engine (`server/app/sim/`) is fully deterministic and decoupled from LLM/network concerns
- `SimulationEngine` owns world state, validates actions, and returns `StepResult` with events and state deltas
- `WorldFactory` creates seeded worlds with guaranteed mission feasibility (enough precious stones)
- Domain models use Python dataclasses with `slots=True` for performance
- Action types are TypedDict unions (`MoveAction | DigAction | ...`)
- The `Broadcaster` singleton fans out events to all WebSocket clients
- Frontend connects via a single WebSocket at `/ws` and receives all state updates as JSON events
- Vite proxies `/api/*` and `/ws` to the backend during development
- Two agent implementations exist: `RoverAgent` (real Mistral LLM calls with `magistral-medium-latest`) and `MockRoverAgent` (random/deterministic fallback)
- AI narration via `narrator.py`: Mistral generates commentary text, ElevenLabs converts to speech with emotion tags; text streams as `narration_chunk` WebSocket events
- GitHub → Discord notifications via `.github/workflows/discord-git-notify.yml` for PR events and main-branch pushes
