# Product Overview

Agent One is a multi-agent LLM-powered Mars mission simulation built for the Mistral Hackathon.

Autonomous agents (Rover, Drone, Station) collaborate in a simulated Mars environment, coordinated by a central Coordinator. Each agent runs its own LLM reasoning loop via the Mistral API to observe world state, evaluate goals, propose actions, and execute tool calls.

The simulation features:
- A deterministic grid-based world with terrain, stones (precious/common), and fog-of-war visibility
- A Rover that moves, digs, picks up stones, and charges at a Station
- Probabilistic goals with confidence tracking (satisfied when `confidence >= threshold`)
- Real-time WebSocket streaming of simulation events to a browser-based mission control UI
- A structured JSON message protocol: `{id, ts, source, type, name, payload, correlation_id}`

The current implementation uses a `MockSimAgent` that picks random legal actions each tick. The full LLM-driven agent loop (observe → reason → act → update confidence → emit actions) is the target architecture.

Agents never communicate directly — all messages route through the Coordinator.
