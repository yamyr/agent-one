# Roadmap

Mars Mission — Multi-Agent LLM Simulation (Mistral Hackathon)

## Milestone 0: Scaffold (pre-hackathon)

- [ ] Init repo, venv, project structure
- [ ] Copy/adapt protocol types from Snowball (subset only)
- [ ] Copy/adapt BaseAgent class (tool framework, streaming, emit helpers)
- [ ] Decide UI approach (terminal with textual/rich? web? both?)

## Milestone 1: Coordinator + Rover (first end-to-end)

**Goal:** send a mission, one agent reasons and acts, world updates.

- [ ] World model: Python dict with zones, rocks, agents, goals, storm level
- [ ] Coordinator: spawn agent subprocess, read/write JSON stdio
- [ ] Coordinator: inject world state slice into agent prompts
- [ ] Coordinator: handle tool calls that mutate world state
- [ ] Rover agent: subclass BaseAgent, Mars system prompt
- [ ] Rover tools: `move_to(zone)`, `drill_sample(rock_id)`, `check_battery()`
- [ ] Test: send "begin mission" -> rover reasons -> executes tool -> world updates

**Done when:** you can chat with the rover and watch it move + drill in the world dict.

## Milestone 2: Drone + Action Piping

**Goal:** two agents running concurrently, communicating through the coordinator.

- [ ] Drone agent: system prompt, scan tools
- [ ] Drone tools: `scan_area(zones)`, `map_route(from, to)`
- [ ] Drone emits Action with probabilistic rock map
- [ ] Coordinator: route Actions from drone -> rover as Send
- [ ] Rover receives drone findings, uses them in reasoning
- [ ] Both agents active simultaneously

**Done when:** drone scans, rover uses scan data to pick a rock, all streamed live.

## Milestone 3: External Events + Human-in-the-loop

**Goal:** dynamic scenario with human decisions.

- [ ] Event system: coordinator fires timed events (storm, terrain shift)
- [ ] Events broadcast to agents as Steer messages with updated world state
- [ ] Agents react to events (rover reassesses, drone adjusts scan priority)
- [ ] Rover emits UiRequest::Confirm before high-risk moves
- [ ] Coordinator presents Confirm/Select to human, routes UiResponse back
- [ ] Human can steer agents with free-text input

**Done when:** storm arrives, rover asks human "cross hazard zone?", human decides, agents adapt.

## Milestone 4: Station Agent + Goal Tracking

**Goal:** full 3-agent setup with visible progress.

- [ ] Station agent: power management, telemetry monitoring
- [ ] Station tools: `allocate_power(agent, amount)`, `broadcast_alert(message)`
- [ ] Station emits PowerBudgetWarning, EmergencyModeActivated actions
- [ ] Goal confidence tracking: updates after each drill, visible in UI
- [ ] Mission completion: goal threshold reached -> mission success message

**Done when:** 3 agents collaborating, goals progressing, mission completes.

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

- [ ] Web UI with zone map
- [ ] Agent positions on map, animated movement
- [ ] Goal confidence bars
- [ ] Event log timeline

## Dependencies

| What | Where |
|------|-------|
| Mistral API key | MISTRAL_API_KEY env var |
| Python 3.12+ | venv |
| mistralai SDK | pip install |
| Snowball protocol subset | copied/adapted from snowball repo |
| BaseAgent class | copied/adapted from agents/mistral_base.py |
