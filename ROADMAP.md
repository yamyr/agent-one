# Roadmap

Mars Mission — Multi-Agent LLM Simulation (Mistral Hackathon)

## Milestone 0: Scaffold (pre-hackathon)

- [x] Init repo, venv, project structure
- [x] Copy/adapt protocol types from Snowball (subset only)
- [x] Copy/adapt BaseAgent class (tool framework, streaming, emit helpers)
- [x] Decide UI approach (terminal with textual/rich? web? both?) → web (Vue 3 + Vite)

## Milestone 1: Rover picks up a stone (first simulation)

**Goal:** rover explores, finds a stone, picks it up. First complete mission loop.

- [x] World model: Python dict with grid, agents, stones
- [x] Async agent loop (no subprocesses)
- [x] Inject world state into agent prompts
- [x] Handle tool calls that mutate world state (`execute_action`)
- [x] Rover agent: RoverAgent (Mistral LLM) + MockRoverAgent (random)
- [x] Rover tools: `move` (cardinal directions), `check_ground` (auto after move)
- [x] Rover memory: visited positions tracked, agents prefer unvisited tiles
- [x] Rover tool: `pick_up` — pick up stone at current position
- [x] Agent inventory: `carrying` field on agent state
- [x] Mission success: rover has a stone in inventory

**Done when:** rover explores the grid, lands on a stone, picks it up. ✅

## Milestone 2: Station Agent

**Goal:** base station agent monitors and supports the rover.

- [x] Station agent: power management, telemetry monitoring
- [x] Station tools: `charge_agent(agent_id)` — charge co-located rovers
- [x] Station tools: `broadcast_alert(message)` — broadcast messages to all agents
- [ ] Station tools: `allocate_power(agent, amount)` — fine-grained power allocation
- [ ] Station emits PowerBudgetWarning, EmergencyModeActivated actions
- [ ] Goal confidence tracking: updates after each drill, visible in UI
- [x] Mission completion: deliver target stones to station → mission success

**Done when:** station monitors rover, manages power, mission completes. (Partial — charging and mission completion done)

## Milestone 3: Drone + Action Piping

**Goal:** two field agents running concurrently, communicating through the coordinator.

- [x] Drone agent: system prompt, scan tools
- [x] Drone tools: `scan` (concentration map), `move` (tile navigation), `notify` (radio to station)
- [x] Drone emits Action with probabilistic rock map
- [x] Coordinator: route Actions from drone → rover (via broadcast + notify)
- [x] Rover receives drone findings, uses them in reasoning
- [x] All agents active simultaneously

**Done when:** drone scans, rover uses scan data to pick a rock, all streamed live. ✅

## Milestone 4: External Events + Human-in-the-loop

**Goal:** dynamic scenario with human decisions.

- [ ] Event system: coordinator fires timed events (storm, terrain shift)
- [ ] Events broadcast to agents with updated world state
- [ ] Agents react to events (rover reassesses, drone adjusts scan priority)
- [ ] Rover emits UiRequest::Confirm before high-risk moves
- [x] Human can steer agents with voice commands (Voxtral STT → LLM parsing → action)

**Done when:** storm arrives, rover asks human "cross hazard zone?", human decides, agents adapt.

## Milestone 5: Demo Script + Polish

**Goal:** reliable, impressive 5-minute demo.

- [ ] Scripted event timeline (timed storms, terrain shifts, escalations)
- [x] Pre-seeded world state tuned for dramatic demo arc (`world_seed` config)
- [x] UI polish: clear layout, streaming visible, tool calls visible (landing page, i18n, responsive)
- [ ] Dry run end-to-end 3+ times
- [x] Handle LLM flakiness: fallback prompts, retry on empty responses (`_fallback_turn()`)
- [x] Cancel works mid-response (`abort_mission()` + task cancellation)

**Done when:** you can run the demo 3 times in a row and it looks good every time.

## Stretch: Voice (ElevenLabs prize)

- [x] TTS reads incoming alerts aloud (ElevenLabs dual-narrator dialogue)
- [x] STT for human commands → coordinator (Voxtral via `/api/voice-command`)
- [x] Agent "personality" voices (Commander Rex = male, Dr. Nova = female narrators)

## Stretch: Visual UI

- [x] Web UI with grid map (Vue 3 + Vite, proxied to FastAPI)
- [x] Agent positions on map, animated movement (SVG with pulsing dots)
- [x] Stone markers on map (diamond shapes, colored by type)
- [ ] Goal confidence bars (UI not implemented)
- [x] Event log timeline (per-agent panes + global event log)
- [x] Agent reasoning transparency panel
- [x] Communication visualization on map
- [x] Landing page with i18n (10 locales) and Three.js Mars globe

## Dependencies

| What | Where |
|------|-------|
| Mistral API key | `MISTRAL_API_KEY` env var |
| ElevenLabs API key | `ELEVENLABS_API_KEY` env var (optional — voice narration) |
| Python 3.14+ | `uv sync` |
| Node.js 24+ | `npm ci` |
| mistralai SDK | `uv sync` (in pyproject.toml) |
| elevenlabs SDK | `uv sync` (optional) |
| SurrealDB | port 4002 (dev) |
| Snowball protocol subset | copied/adapted from snowball repo |
| BaseAgent class | copied/adapted from agents/mistral\_base.py |
