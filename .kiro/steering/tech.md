# Tech Stack & Build

## Backend (server/)
- Python 3.12+
- FastAPI (web framework, WebSocket support)
- uvicorn (ASGI server)
- SurrealDB (database, port 4002 dev / 8009 test)
- pydantic-settings (configuration via `.env`)
- mistralai SDK (LLM integration — `magistral-medium-latest` for narration + agent reasoning)
- elevenlabs SDK (optional TTS for voice narration)
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
- `ELEVENLABS_API_KEY` — optional, enables voice narration (text narration works without it)
- `NARRATION_ENABLED`, `NARRATION_VOICE_ID`, `NARRATION_MIN_INTERVAL_SECONDS` — narration config
- Server config via `server/.env` (see `server/env.sample`)
- Settings managed by pydantic-settings in `server/app/config.py`

## CI/CD
- GitHub Actions CI (`.github/workflows/ci.yml`): ruff lint, rut tests + SurrealDB, eslint + vite build, Docker build verify
- Discord notifications (`.github/workflows/discord-git-notify.yml`): PR and main-push events sent to Discord via webhooks
- Secrets: `DISCORD_WEBHOOK_URL` (default), `DISCORD_WEBHOOK_URL_PR` (optional), `DISCORD_WEBHOOK_URL_MAIN` (optional)

## Ports
| Service          | Port |
|------------------|------|
| Server (FastAPI) | 4009 |
| UI (Vite)        | 4089 |
| SurrealDB (dev)  | 4002 |
| SurrealDB (test) | 8009 |
