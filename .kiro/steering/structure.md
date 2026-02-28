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
│   │   ├── agent.py            # RoverAgent (Mistral LLM) + MockRoverAgent (legacy)
│   │   ├── sim_agent.py        # MockSimAgent wrapping SimulationEngine (current demo agent)
│   │   ├── world.py            # Legacy world model (dict-based zones)
│   │   └── sim/                # Deterministic simulation engine
│   │       ├── models.py       # Domain models: WorldState, RoverState, StationState, GridState, etc.
│   │       ├── engine.py       # SimulationEngine: validates actions, advances world state
│   │       ├── world_factory.py# WorldFactory: seeded world creation with guaranteed feasibility
│   │       └── errors.py       # Error constants (INVALID_OUT_OF_BOUNDS, etc.)
│   ├── tests/
│   │   ├── conftest.py         # In-memory SurrealDB setup, CaseWithDB base class
│   │   ├── test_sim_engine.py  # SimulationEngine unit tests
│   │   └── ...                 # Other test modules
│   ├── pyproject.toml          # Python project config (uv, ruff)
│   ├── uv.lock                 # Locked dependencies
│   └── run                     # Dev server start script
├── ui/                         # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── App.vue             # Root component, WebSocket connection, layout
│   │   ├── main.js             # Vue app entry point
│   │   └── components/
│   │       ├── MarsGrid.vue    # Grid-based surface map visualization
│   │       ├── RoverTelemetry.vue # Rover status, battery, mission progress
│   │       └── EventLog.vue    # Scrolling event log
│   ├── vite.config.js          # Vite config with proxy to backend
│   └── package.json
├── Dockerfile                  # Multi-stage: Node build → Python runtime
├── railway.toml                # Railway deployment config
├── SPEC.md                     # Full system specification
├── IDEA.md                     # High-level vision
├── ROADMAP.md                  # Milestone plan (M0–M5)
└── tasks/todo.md               # Task tracking
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
- Two agent implementations exist: `RoverAgent` (real Mistral LLM calls) and `MockSimAgent` (random actions for demo)
- `world.py` is a legacy dict-based world model; `sim/` is the current engine
