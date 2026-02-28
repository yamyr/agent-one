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

## Best Practices to adhere to
- Before working on any changes on the codebase, create a new feature branch and do the changes in this dedicated feature branch. Once the implementation is done, ensure complete test coverage, full documentation and then submit a Pull Request (PR) and merge it into main if all tests are passing.
- After each change to the codebase, update the Changelog.md file and report what was changed as well as what errors have been identified to prevent from duplicate or similar errors happening again.
- After each change to the codebase, also scan the repo for any bloated code or in-efficient implementations. The repo has a very strong emphasis on accuracy and performance.
- Ensure that the website is optimized for computers/laptops, tablets and mobile phones using a responsive design.
- If you need to look up the latest documentation for an external tool, e.g., Vercel, Supabase, etc., please include 'use context7' in your prompt
- For each new task, please first create a plan in a markdown file in this repo such that we can always trace back at which stage of the implementation for this particular task we currenlty are by comparing the code and then what's in the plan. Also, divide each plan into smaller tasks and sub-tasks that **shall** be marked as completed in this markdown file if done so. -->

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

---

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

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
