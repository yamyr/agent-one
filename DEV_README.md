# Dev Setup

## Prerequisites

- Python 3.12+
- Node >= 22.12.0
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [SurrealDB](https://surrealdb.com/install) (running on port 4002 for dev)

## Server

```bash
cd server
uv sync
./run              # starts uvicorn on :4009 with --reload
```

Create `server/.env` for local config:

```
MISTRAL_API_KEY=your-key-here
```

### Tests

```bash
cd server
rut tests/                                                    # all tests
rut tests/test_health.py                                      # single file
rut tests/test_health.py::TestHealth::test_health_returns_ok  # single test
```

Tests spawn an in-memory SurrealDB instance automatically (port 8009).

## UI

```bash
cd ui
npm install
npm run dev        # starts vite on :4089
```

Vite proxies `/api/*` and `/ws` to the server at `localhost:4009`.

## Ports

| Service          | Port |
|------------------|------|
| Server (FastAPI) | 4009 |
| UI (Vite)        | 4089 |
| SurrealDB (dev)  | 4002 |
| SurrealDB (test) | 8009 |
