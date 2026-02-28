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

## Dependencies

| What | Detail |
|------|--------|
| Python | 3.12+ |
| LLM SDK | `mistralai` (pip install) |
| API key | `MISTRAL_API_KEY` env var |
| Base code | Protocol types and BaseAgent adapted from Snowball |

## Key Spec References

- `SPEC.md` — full system spec: world model, agent tools, event/action system, message schema, demo timeline
- `IDEA.md` — high-level concept and vision
- `ROADMAP.md` — milestone plan (M0–M5 + stretch goals)
- `_private/PROTOCOL_REF.md` — protocol reference from Snowball
