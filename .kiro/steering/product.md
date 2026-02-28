# Product Overview

Agent One is a multi-agent LLM-powered Mars mission simulation built for the Mistral Hackathon.

Autonomous agents (Rover, Drone, Station) collaborate in a simulated Mars environment, coordinated by a central Coordinator. Each agent runs its own LLM reasoning loop via the Mistral API to observe world state, evaluate goals, propose actions, and execute tool calls.

The simulation features:
- A deterministic grid-based world with terrain, hidden stone types (core/basalt with `analyze` to reveal), fog-of-war visibility, and concentration maps
- Rovers that move, dig, analyze, pick up stones, and charge at a Station — starting at station (0,0) and exploring outward
- Per-rover visibility radius shown as colored dashed circles on the map
- Probabilistic goals with confidence tracking (satisfied when `confidence >= threshold`)
- Real-time WebSocket streaming of simulation events to a browser-based mission control UI
- AI narration: Mistral LLM generates live commentary with optional ElevenLabs TTS voice synthesis (streaming text via `narration_chunk` events)
- GitHub → Discord webhook notifications for PR and main-branch push events
- A structured JSON message protocol: `{id, ts, source, type, name, payload, correlation_id}`

Two agent implementations exist: `RoverAgent` (real Mistral LLM calls with `magistral-medium-latest`) and `MockRoverAgent` (random/deterministic fallback for demo). Rovers explore autonomously without station-rover communication.

Agents never communicate directly — all messages route through the Coordinator.
