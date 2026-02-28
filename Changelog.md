# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Infinite Grid with Viewport & Minimap**: World is no longer a fixed 20×20 grid
  - Chunk-based procedural generation: 16×16 tile chunks generated lazily as agents explore
  - Seeded/deterministic world: each chunk uses `sha256(world_seed:cx:cy)` for consistent generation
  - No boundaries: agents can move to any integer coordinate (negative included)
  - Per-chunk stone placement with origin chunk guaranteed ≥1 core stone
  - Hash-based noise concentration map with core-proximity boosting
  - Explored bounds tracking in `WORLD["bounds"]`
  - **Viewport camera**: 20×20 tile viewport that pans over the infinite world
  - **Auto-follow**: Camera tracks most recently moved agent by default
  - **Drag-to-pan**: Click-drag to manually navigate; double-click to re-enable auto-follow
  - **MiniMap component**: Reduced-scale overview of all explored terrain with viewport rectangle overlay and click-to-navigate
  - 7 new chunk system tests (149 total pass)

- **Entity Follow Selector**: UI controls to select which agent the camera tracks
  - Follow buttons for each mobile agent (rovers, drone) plus "Free" camera mode
  - Buttons styled with agent colors, highlight when active
  - Drag-to-pan automatically switches to free camera mode
  - No auto-follow by default — user chooses which entity to track

- **Battery Safety Return-to-Base**: Critical safety feature ensuring agents never strand
  - `must_return_to_base()` function calculates Manhattan distance to station × move cost + 6% safety margin
  - Battery check is the FIRST priority in both `_update_rover_tasks` and `_update_drone_tasks`
  - Overrides ALL other tasks (exploration, stone collection, scanning) when battery is critical
  - MockRoverAgent and MockDroneAgent enforce return-to-base at agent level (hard override)
  - Task system generates urgent "⚠️ LOW BATTERY" messages for LLM agents

- **Drone Scout Agent**: Aerial drone entity that scouts terrain for precious stone deposits
  - `DroneAgent` (LLM-powered via Mistral) + `MockDroneAgent` (deterministic fallback) in `agent.py`
  - Drone flies 1-6 tiles per move at 1% battery/tile (rovers: 1-3 tiles at 2%)
  - `scan` action: samples concentration map around drone position, returns probability readings
  - `drone_scans` shared memory: rovers read scan results and navigate toward high-concentration hotspots
  - Drone is a pure scout — cannot dig, analyze, or pick up stones
  - Per-agent reveal radius: `ROVER_REVEAL_RADIUS=3`, `DRONE_REVEAL_RADIUS=6`
  - Per-agent max move distance: rovers 3 tiles, drone 6 tiles
  - Purple triangle marker on UI map with larger dashed visibility circle
  - 12 new drone unit tests (142 total pass)

### Changed

- Grid system replaced: fixed `GRID_W`/`GRID_H` boundaries removed; world is now unbounded
- `_cells_in_radius` no longer clamps to grid bounds (returns full diamond)
- `move_agent` no longer rejects out-of-bounds moves
- `_update_drone_tasks` searches within 30-tile radius around agent instead of full grid
- `get_snapshot()` includes `bounds` field and strips internal chunk data
- Rover visibility radius reduced from 5 to 3 tiles (balanced by drone's 6-tile radius)
- `update_tasks()` split into `_update_rover_tasks()` and `_update_drone_tasks()`
- Rovers now check `drone_scans` for hotspots when no visible stones are found
- WorldMap camera control changed from auto-follow to parent-driven `followAgent` prop
- MockRoverAgent and MockDroneAgent exploration now works with infinite grid (removed boundary clamping)

- **ElevenLabs AI Narration**: Real-time narration of Mars mission events via ElevenLabs TTS
  - `server/app/narrator.py` — narration engine with event filtering (drama weights 1-3), Mistral LLM text generation ("David Attenborough meets space podcaster" persona), ElevenLabs TTS audio conversion, async event batching, and rate limiting
  - `ui/src/components/NarrationPlayer.vue` — audio player with base64 MP3 playback queue, skip/mute controls, pulsing mic icon, responsive layout
  - WebSocket `narration` event type (`{source: "narrator", type: "narration", payload: {text, audio, format}}`) for real-time audio delivery
  - `/narration/toggle` POST and `/narration/status` GET endpoints for runtime control
  - `ELEVENLABS_API_KEY`, `NARRATION_ENABLED`, `NARRATION_VOICE_ID`, `NARRATION_MIN_INTERVAL_SECONDS` config settings
  - Narrator hooks into simulation lifecycle: starts/stops/resets with simulation, feeds on all broadcast events

- **Upgraded TTS model to ElevenLabs v3**: replaced `eleven_flash_v2_5` with `eleven_v3` for premium voice quality with emotional expression
- Updated narrator system prompt to leverage v3 audio tags (`[whispers]`, `[gasps]`, `[laughs]`, `[sighs]`, `[clears throat]`) for dramatic vocal inflection during mission narration

### Changed


### Changed

- Removed `check_ground` from rover actions — ground is now auto-scanned after every move
- Removed `charge` from rover actions — charging is now station-only via `charge_rover()`
- Mission success now requires delivering target stones to the station, not just collecting them
- Station agent can charge rovers (new `charge_rover` tool) and auto-charges them on arrival
- Mock rover now digs/picks up stones and navigates back to station when carrying target stone
- Updated rover system prompt with auto-charge and return-to-base instructions
- **Coordinate system flipped to math convention**: north = +Y, south = -Y; (0,0) renders at bottom-left of the map
- **Stone types are now hidden**: all stones spawn as `"unknown"` with a hidden `_true_type`; rovers must `analyze` before digging/picking up
- Stone generation uses **preferential attachment clustering** — core stones cluster together instead of uniform random placement

### Added

- **`analyze` action**: reveals a stone's true type (core/basalt), costs 3% battery; dig/pickup now require prior analysis
- **`analyze_ground` action**: reads ground concentration at current tile (0.0–1.0 indicating proximity to core deposits), costs 3% battery; readings stored in agent memory
- **Concentration map**: computed from core positions using Gaussian falloff (`exp(-d²/σ²)`, σ=4.0), serialized in snapshots for UI access
- Dynamic **task priority system** in `update_tasks()`: return-to-station > analyze > dig > pickup > navigate-to-stone > explore
- `_direction_hint()` helper for human-readable navigation hints in agent context
- GitHub Actions CI pipeline (`.github/workflows/ci.yml`) with 5 jobs: change detection, server lint (ruff), server test (rut + SurrealDB), UI lint + build (eslint + vite), and Docker build verification
- ESLint 9 flat config for Vue 3 frontend (`ui/eslint.config.js`)
- `unknown` stone color (`#4a4a6a`) in UI constants and AgentDetailModal CSS
- Snapshot filtering: `_true_type` stripped from broadcast to prevent UI leaking hidden info

### Fixed

- `rut` test runner dependency changed from broken local path to git source (`server/pyproject.toml`)
- SurrealDB readiness check in test conftest hardened with retry loop instead of fragile `time.sleep(1)` (`server/tests/conftest.py`)
- Ruff formatting applied to `server/app/agent.py` and `server/app/world.py`
- Removed unused `props` variable assignment in `MissionBar.vue` to fix ESLint `no-unused-vars` error
- Added Release Please annotation to FastAPI app version in `server/app/main.py` to prevent version drift across releases
- Updated rover task planning in `server/app/world.py` to keep revealed-tile filtering lint-clean in CI
- Applied Ruff formatting to `server/app/world.py` and `server/tests/test_world.py` to keep merge-ref CI formatting checks green
- Fixed Release Please TOML version path in `release-please-config.json` so `server/pyproject.toml` bumps on every release
- Made agent turn interval configurable via `agent_turn_interval_seconds` (mock, 0.5s) and `llm_turn_interval_seconds` (LLM, 3.0s) to prevent Mistral API rate-limit pressure
- Added RoverAgent runtime fallback so `rover-mistral` keeps moving with deterministic mock logic when LLM calls fail or return no tool action
- Narrowed RoverAgent exception handling from broad `Exception` to `(SDKError, ConnectionError, TimeoutError, RuntimeError)` so programming bugs surface instead of being silently swallowed
- Cached mock fallback instance in RoverAgent instead of creating a new `MockRoverAgent` per failure
- Added logging for hallucinated tool names and LLM thinking when no valid tool action is returned
- Installed GitHub Spec Kit (`github/spec-kit`) with shorthand aliases: `/c`, `/s`, `/p`, `/t`, `/i`, `/t2i`
- ESLint config now ignores `dist/` and `node_modules/` build output
- Auto-fixed 148 Vue template formatting warnings (attribute line breaks, indentation)
- Added `default` or `required` to all Vue component props to resolve 18 `vue/require-default-prop` warnings — zero ESLint warnings remain
