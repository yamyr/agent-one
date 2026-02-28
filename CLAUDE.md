# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent LLM-powered Mars mission simulation for the Mistral Hackathon (Feb 28 – Mar 1). Three autonomous agents (Rover, Drone, Station) collaborate in a simulated Mars environment, coordinated by a central Coordinator. Each agent runs its own LLM reasoning loop (Mistral API) to evaluate goals, propose actions, and execute tool calls.

## Architecture

- **Coordinator**: Spawns agent subprocesses, injects world state into prompts, routes messages/actions between agents, handles timed events (storms, terrain shifts). Agents communicate through the Coordinator — never directly.
- **Agents**: Rover (move, drill, carry), Drone (scan, map routes, relay), Station (power allocation, alerts). Each runs an observe → reason (LLM) → act → update-confidence loop.
- **World Model**: Python dict holding zones, rocks, agent positions/battery/mobility, storm level, hazards. Updated by tool call results and external events.
- **Protocol**: JSON messages with `{id, ts, source, type, name, payload, correlation_id}`. Types: event, action, command, tool, stream.
- **Goals**: Probabilistic — each goal has a `confidence` (0.0–1.0) updated dynamically, satisfied when `confidence >= threshold`.

Agent classes and protocol types are adapted from the Snowball project (`snowball` repo).

## Project Structure

- `server/` — Python FastAPI backend (port 4009)
- `ui/` — Vue 3 + Vite frontend (port 4089)

## Server

Uses FastAPI with SurrealDB and pydantic-settings. Managed with `uv`.

```bash
cd server
uv sync                        # install deps
./run                          # uvicorn on :4009 with --reload
rut tests/                     # run all tests
rut tests/test_health.py       # run single test file
rut tests/test_health.py::TestHealth::test_health_returns_ok  # single test
```

Key modules:
- `app/main.py` — FastAPI app, lifespan (DB init/close), CORS, health endpoint
- `app/config.py` — pydantic-settings (`Settings`), reads `.env`
- `app/db.py` — SurrealDB connection helpers, `get_db()` generator for request-scoped connections
- `app/broadcast.py` — `Broadcaster` singleton for WebSocket fan-out
- `app/views.py` — REST endpoints + `/ws` WebSocket endpoint

Tests use `rut` (unittest runner) with in-memory SurrealDB spawned in `conftest.py` (`rut_session_setup`/`rut_session_teardown`). Base class `CaseWithDB` provides per-test DB isolation.

## UI

```bash
cd ui
npm install
npm run dev                    # vite on :4089
```

Vite proxies `/api/*` to `http://localhost:4009` and `/ws` to `ws://localhost:4009`. Single-page app connects via WebSocket to receive real-time simulation events.

## Dependencies

| What | Detail |
|------|--------|
| Python | 3.12+ |
| LLM SDK | `mistralai` |
| API key | `MISTRAL_API_KEY` env var |
| SurrealDB | running on port 4002 (dev) |
| Node | >= 22.12.0 |
| Base code | Protocol types and BaseAgent adapted from Snowball |

## Key Spec References

- `SPEC.md` — full system spec: world model, agent tools, event/action system, message schema, demo timeline
- `IDEA.md` — high-level concept and vision
- `ROADMAP.md` — milestone plan (M0–M5 + stretch goals)
- `_private/PROTOCOL_REF.md` — protocol reference from Snowball
