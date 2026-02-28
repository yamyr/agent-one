# Roadmap

Mars Mission — Multi-Agent LLM Simulation (Mistral Hackathon)

## Milestone 0: Scaffold (pre-hackathon)

- [x] Init repo, venv, project structure
- [ ] Copy/adapt protocol types from Snowball (subset only)
- [ ] Copy/adapt BaseAgent class (tool framework, streaming, emit helpers)
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
- [ ] Rover tool: `pick_up` — pick up stone at current position
- [ ] Agent inventory: `carrying` field on agent state
- [ ] Mission success: rover has a stone in inventory

**Done when:** rover explores the grid, lands on a stone, picks it up.

## Milestone 2: Station Agent

**Goal:** base station agent monitors and supports the rover.

- [ ] Station agent: power management, telemetry monitoring
- [ ] Station tools: `allocate_power(agent, amount)`, `broadcast_alert(message)`
- [ ] Station emits PowerBudgetWarning, EmergencyModeActivated actions
- [ ] Goal confidence tracking: updates after each drill, visible in UI
- [ ] Mission completion: goal threshold reached -> mission success message

**Done when:** station monitors rover, manages power, mission completes.

## Milestone 3: Drone + Action Piping

**Goal:** two field agents running concurrently, communicating through the coordinator.

- [ ] Drone agent: system prompt, scan tools
- [ ] Drone tools: `scan_area(zones)`, `map_route(from, to)`
- [ ] Drone emits Action with probabilistic rock map
- [ ] Coordinator: route Actions from drone -> rover
- [ ] Rover receives drone findings, uses them in reasoning
- [ ] All agents active simultaneously

**Done when:** drone scans, rover uses scan data to pick a rock, all streamed live.

## Milestone 4: External Events + Human-in-the-loop

**Goal:** dynamic scenario with human decisions.

- [ ] Event system: coordinator fires timed events (storm, terrain shift)
- [ ] Events broadcast to agents with updated world state
- [ ] Agents react to events (rover reassesses, drone adjusts scan priority)
- [ ] Rover emits UiRequest::Confirm before high-risk moves
- [ ] Human can steer agents with free-text input

**Done when:** storm arrives, rover asks human "cross hazard zone?", human decides, agents adapt.

## Milestone 5: Demo Script + Polish

**Goal:** reliable, impressive 5-minute demo.

- [ ] Scripted event timeline (timed storms, terrain shifts, escalations)
- [ ] Pre-seeded world state tuned for dramatic demo arc
- [ ] UI polish: clear layout, streaming visible, tool calls visible
- [ ] Dry run end-to-end 3+ times
- [ ] Handle LLM flakiness: fallback prompts, retry on empty responses
- [ ] Cancel works mid-response

**Done when:** you can run the demo 3 times in a row and it looks good every time.

## Stretch: Voice (ElevenLabs prize)

- [ ] TTS reads incoming alerts aloud
- [ ] STT for human commands -> coordinator
- [ ] Agent "personality" voices (rover = calm, station = urgent)

## Stretch: Visual UI

- [x] Web UI with grid map (Vue 3 + Vite, proxied to FastAPI)
- [x] Agent positions on map, animated movement (SVG with pulsing dots)
- [x] Stone markers on map (diamond shapes, colored by type)
- [ ] Goal confidence bars
- [x] Event log timeline (per-agent panes + global event log)

## Dependencies

| What | Where |
|------|-------|
| Mistral API key | MISTRAL_API_KEY env var |
| Python 3.12+ | venv |
| mistralai SDK | pip install |
| Snowball protocol subset | copied/adapted from snowball repo |
| BaseAgent class | copied/adapted from agents/mistral_base.py |
