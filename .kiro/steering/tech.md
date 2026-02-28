# Tech Stack & Build

## Backend (server/)
- Python 3.12+
- FastAPI (web framework, WebSocket support)
- uvicorn (ASGI server)
- SurrealDB (database, port 4002 dev / 8009 test)
- pydantic-settings (configuration via `.env`)
- mistralai SDK (LLM integration)
- rich (logging)
- uv (package manager, replaces pip)
- ruff (linter, line-length 100)

## Frontend (ui/)
- Vue 3 (Composition API with `<script setup>`)
- Vite 7 (dev server on port 4089, proxies to backend)
- Node >= 22.12.0
- ESLint with eslint-plugin-vue

## Testing
- unittest (Python standard library, not pytest)
- `rut` as the test runner (custom runner, not pytest)
- Tests spawn an in-memory SurrealDB instance automatically
- `CaseWithDB` base class provides per-test DB isolation

## Deployment
- Docker multi-stage build (Node build → Python runtime)
- Railway (railway.toml config)
- Health check at `/health`

## Common Commands

```bash
# Server
cd server
uv sync                          # install dependencies
./run                            # start dev server (uvicorn :4009 --reload)
rut tests/                       # run all tests
rut tests/test_sim_engine.py     # run single test file
rut tests/test_sim_engine.py::TestSimEngine::test_move_updates_position_and_battery  # single test

# UI
cd ui
npm install                      # install dependencies
npm run dev                      # start vite dev server (:4089)
npm run build                    # production build
npm run lint                     # lint with eslint --fix

# Database
cd server
./start_db                       # start SurrealDB for development

# Docker
docker build -t agent-one .      # full build
```

## Environment Variables
- `MISTRAL_API_KEY` — required for LLM agent functionality
- Server config via `server/.env` (see `server/env.sample`)
- Settings managed by pydantic-settings in `server/app/config.py`

## Ports
| Service          | Port |
|------------------|------|
| Server (FastAPI) | 4009 |
| UI (Vite)        | 4089 |
| SurrealDB (dev)  | 4002 |
| SurrealDB (test) | 8009 |
