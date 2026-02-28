# Implementation Plan: Update ROADMAP.md Checkboxes

**Feature Branch**: `074-update-roadmap`  
**Created**: 2026-03-01

## Overview

Update ROADMAP.md milestone checkboxes and dependency info to accurately reflect the current implementation state. Correct drone tool names to match actual codebase.

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `ROADMAP.md` | Modify | Update 11 checkboxes, correct tool names, update 2 dependency entries |
| `Changelog.md` | Modify | Add/update docs entry under [Unreleased] |

## Changes

### Commit 1 (0fc38b9 — already landed)
1. M0 line 8: `[ ] Copy/adapt protocol types` → `[x]` (protocol.py exists)
2. M0 line 9: `[ ] Copy/adapt BaseAgent class` → `[x]` (base_agent.py exists)
3. M3 line 46: `[ ] Drone agent` → `[x]` (DroneAgent in agent.py)
4. M3 line 51: `[ ] All agents active simultaneously` → `[x]` (main.py active_agents)
5. Stretch Voice line 82: `[ ] TTS reads alerts aloud` → `[x]` (narrator.py + ElevenLabs)
6. Dependencies line 99: `Python 3.12+ | venv` → `Python 3.14+ | uv sync`
7. Dependencies line 100: `mistralai SDK | pip install` → `mistralai SDK | uv sync`

### Commit 2 (this commit)
8. M3 line 47: Correct tool names from `scan_area(zones)`, `map_route(from, to)` → `scan` (concentration map), `move` (tile navigation)
9. M3 line 48: `[ ] Drone emits Action with probabilistic rock map` → `[x]` (_execute_scan in world.py)
10. M3 line 49: `[ ] Coordinator: route Actions from drone → rover` → `[x]` (_best_drone_hotspot in world.py)
11. M3 line 50: `[ ] Rover receives drone findings` → `[x]` (rover tasks use hotspot data)
12. Update Changelog.md entry to include tool name corrections and action piping completion

## Verification

Each checkbox verified by inspecting actual source files:
- `server/app/protocol.py` — protocol message types
- `server/app/base_agent.py` — BaseAgent class
- `server/app/agent.py` — DroneAgent class
- `server/app/world.py` — scan tool, `_best_drone_hotspot()`, action piping
- `server/app/narrator.py` — ElevenLabs TTS
- `server/app/main.py` — concurrent agent activation
