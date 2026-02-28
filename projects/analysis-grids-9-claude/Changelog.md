# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (Help Popup)

- **Help popup modal**: New `HelpPopup.vue` component accessible via "HELP" button in AppHeader and "?" keyboard shortcut
  - Drone capabilities: scanning, route mapping, relay communications
  - Movement limits: Rover ±1 tile/turn, Drone ±2 tiles/turn, Station fixed
  - Limitations: storm damage, communication range, carry capacity, battery thresholds
  - Battery mechanics: full charge 100%, drone minimum 20%, move/scan costs, charge rate at station
  - Keyboard controls: Space (pause), Arrow keys (pan), 1-3 (follow agent), 0 (free camera), Esc (close modals)
- **Responsive design**: Help popup adapts to tablet and mobile screens with adjusted layouts (movement cards as rows on mobile)

### Added (Storm Events)

- **Dynamic storm system**: Timed storm events that broadcast to all agents with configurable severity levels (1-3)
- **Environmental effects**: Storms reduce visibility (100% → 40% at level 3), lower temperature (-35°C → -65°C), and create urgency
- **Agent adaptation**: All agents receive storm information in their context and can adapt behavior (rovers may shelter, drones may return, station alerts)
- **Narrator drama**: Dual narrators react dramatically to storm events with enhanced dialogue generation
- **Automatic scheduling**: Storms occur randomly (every 30-80 ticks) with durations of 10-30 ticks

### Added (Multi-language Support)

- **Database-backed translations**: Translations stored in SurrealDB with API endpoints for management
- **Language switching**: UI language selector in AppHeader with support for English, Spanish, French, German, Chinese, and Japanese
- **Translation API**: `/translations/{language}` endpoint returns all translations, `/translations/languages` returns supported languages
- **Extensible system**: Easy to add new languages and translation keys through the database

### Changed (UI Clean Up)

- Map and minimap now render the grid even before world state arrives (consistent UI layout)
- Removed "Waiting for world state..." and "Waiting for mission events..." placeholder messages (cleaner empty state)

### Changed (Basalt Vein System)

- **Vein-based mineral system**: Replaced binary stone types (core/basalt) with a vein grade system. Every vein is basalt with a grade (low/medium/high/rich/pristine) determining quantity, following exponential rarity decay (`weight = 200 * e^(-1.3 * index)`)
- **Vein data model**: Each vein has hidden `_true_grade` and `_true_quantity` fields revealed on analyze. Grades map to quantity ranges: low (10-50), medium (51-150), high (151-350), rich (351-700), pristine (701-1000)
- **Quantity-based missions**: Mission success now requires collecting a target quantity of basalt (default 100 units) rather than a count of specific stone types. `target_count`/`collected_count` replaced with `target_quantity`/`collected_quantity`
- **Concentration map scaling**: Ground concentration boost near veins now scales with grade index — higher-grade veins produce stronger signals
- **Task planning**: Rover task generation prioritizes higher-grade veins (pristine first) when choosing navigation targets
- **Agent prompts**: All rover, drone, and station LLM prompts updated for vein terminology — tool descriptions, workflow instructions, and context display reference grades and quantities
- **Narrator keywords**: Updated narration keyword filter from "core" to "vein"
- **UI vein visualization**: Stone rendering replaced with grade-based colors (pristine=gold, rich=deep gold, high=amber, medium=silver, low=gray) and size scaling (6-14px by grade). Rich/pristine veins get SVG glow effect
- **UI inventory display**: Agent detail modal shows grade + quantity per vein (e.g., "HIGH x237")
- **UI mission progress**: Mission bar shows quantity-based progress (e.g., "237 / 100 basalt")
- **Pydantic models**: `StoneInfo` and `InventoryItem` gained `grade` and `quantity` fields; `RoverWorldView` uses `target_quantity`/`collected_quantity`
- **Test coverage**: 278 tests passing — added `TestVeinGradeDistribution` (5 tests) validating exponential rarity, updated all stone-related test classes for vein data structures

### Added (Solar Panels)

- **Solar panel system**: Rovers carry 2 deployable solar panels (`MAX_SOLAR_PANELS=2`). Deploy with `deploy_solar_panel` action (costs 1 fuel), recharge with `use_solar_battery` (gains 25% battery). Panels render on the map as gold rectangles (grey when depleted).
- **Solar panel tools**: `DEPLOY_SOLAR_PANEL_TOOL` and `USE_SOLAR_BATTERY_TOOL` added to rover LLM tool list.
- **Solar panel context**: Rover LLM prompt includes panels remaining and nearby panel status.
- **Solar panel rendering**: WorldMap.vue renders active/depleted panels with grid lines.
- **`_nearest_solar_panel` helper**: Low-battery task hints suggest nearby active panels as alternative to station return.

### Changed (Remove Mock Rover)

- **Removed `rover-mock` agent entirely**: `MockRoverReasoner`, `MockRoverAgent`, `RoverMockLoop` classes deleted from `agent.py`. No more mock rover in `_build_initial_world`, `AGENT_MAP`, `active_agents` config, or `AGENT_COLORS`.
- **`MistralRoverReasoner._fallback_turn`**: Now uses inline explore logic (random unvisited direction) instead of delegating to `MockRoverReasoner`.
- **`charge_rover` → `charge_agent`**: Renamed to accept any non-station agent (drone included). `charge_rover` kept as backward-compat alias.
- **Station prompt**: Updated to reference single rover `rover-mistral` instead of two rovers.

### Changed (Mission Return Logic)

- **Mission fulfillment check**: `_update_rover_tasks` now checks quantity-based fulfillment and instructs rover to return to station immediately with emoji prefix.
- **Rover LLM prompt**: Added "CRITICAL: Once you have collected enough basalt, STOP exploring and RETURN TO STATION IMMEDIATELY."
- **Mission indicator**: LLM context shows mission target met status when collected quantity meets target.

### Changed (UI Improvements)

- **Chronological event log**: `AgentPane.vue` now shows ALL events (thinking + actions) chronologically, not just thinking events. Actions show move coordinates or result text.
- **CSS refinements**: `.ae-type.think` colored `#668`, `.ae-text.action-text` colored `#7a9a7a`.

### Lessons Learned

- When spawning agent teams with file-editing permissions, coordinate edits carefully — concurrent writes to the same file cause "file modified since read" conflicts. Assign file ownership per agent to avoid collisions.
- When replacing a mock with real agent, test setUp methods that previously initialized two agents need careful deduplication.
- Mission state (`collected_quantity`) must be reset in test setUp to avoid cross-test contamination with new mission-fulfillment logic.

### Changed (Battery & Fuel Rebalance)

- **Fuel capacity system**: Rovers carry 350 fuel units, Drone carries 250 fuel units. Battery remains a 0.0–1.0 float (fraction of capacity)
- **1 fuel unit per tile**: All agents now cost 1 fuel unit per tile moved (~0.29% battery for rovers, ~0.4% for drone)
- **Action costs (in fuel units)**: move=1/tile, dig=6, analyze=3, pickup=2, scan=2. All expressed as fuel units divided by capacity
- **Return-to-base at 67%**: Agents must return to station when battery drops to 67% or below (dual check: threshold + distance safety net with 6% margin)
- **Constants centralized**: All battery costs use named constants from `world.py` — no more hardcoded magic numbers in `agent.py`
- **Updated LLM prompts**: Rover and drone system prompts now describe costs in fuel units with percentage equivalents
- **Updated tool descriptions**: All tool descriptions in `agent.py`, `world.py`, and `station.py` use fuel-unit-based costs
- **Documentation updated**: `WORLD.md` reflects new fuel capacity system and return-to-base rules

### Changed (Runtime Upgrade)

- **Python 3.12 → 3.14**: Updated `server/pyproject.toml` (`requires-python`), CI workflow (`python-version`), Dockerfile (`python:3.14-slim`), regenerated `uv.lock`
- **Node 22 → 24 LTS**: Updated `ui/package.json` (`engines.node`), CI workflow (`node-version`), Dockerfile (`node:24-slim`)
- Updated docs: `CLAUDE.md`, `README.md`, `DEV_README.md` to reflect new version requirements

### Added (Co-Authoring Guidelines)

- **Co-authoring standard**: All commits and PRs now use `Co-Authored-By: agent-one team <agent-one@yanok.ai>` — added to CLAUDE.md as mandatory rule and to PR template footer
- Replaces per-model attribution (e.g., `Claude Opus`) with unified team identity

### Added (Semantic PR Logs)

- **PR template** (`.github/PULL_REQUEST_TEMPLATE.md`): standardized semantic PR format with change type checkboxes, semantic diff (Added/Changed/Removed), file impact table (files added/modified/deleted, lines +/-), core files listing, and test coverage section
- **CLAUDE.md instructions** for auto-generating PR bodies: computes git diff stats, classifies files by filter (A/M/D), identifies core vs test files, and fills the template programmatically

### Added (Dual Narrators)

- **Dual-narrator dialogue system**: Two narrators — Commander Rex (male, dry humor) and Dr. Nova (female, science enthusiast) — banter about mission events in real time
  - `server/app/narrator.py` fully rewritten: new `NARRATOR_SYSTEM_PROMPT` defining both characters, `_parse_dialogue()` regex parser for `COMMANDER REX: ...` / `DR. NOVA: ...` output, `_generate_dialogue_audio()` using ElevenLabs Text-to-Dialogue API (`text_to_dialogue.convert()` with `DialogueInput` pairs), single-voice fallback via `_generate_audio_single()`
  - WebSocket narration payload now includes `dialogue: [{speaker, text}, ...]` alongside flat `text` for backward compatibility
  - `NarrationPlayer.vue` updated: speaker-labeled dialogue lines (REX in amber `#cc8844`, NOVA in teal `#44ccaa`), label changed from "NARRATOR" to "MISSION COMMS"
  - Config: `narration_voice_id_male` (George), `narration_voice_id_female` (Rachel), `narration_model` (`mistral-medium-latest`)
  - 14 new unit tests: `TestParseDialogue` (8 tests) and `TestStripAudioTags` (6 tests) covering dialogue parsing, speaker normalization, audio tag stripping

### Changed (Dual Narrators)

- Narration model switched from `magistral-medium-latest` to `mistral-medium-latest` (user-specified)
- Narration max tokens increased from 200 to 350 to accommodate dialogue format
- Config field `narration_voice_id` replaced with `narration_voice_id_male` and `narration_voice_id_female`

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

- **GitHub → Discord webhook notifications**: New workflow `.github/workflows/discord-git-notify.yml` sends PR and main-branch push events to Discord channels
  - Separate jobs for PR events (opened/reopened/synchronize/ready_for_review/closed/merged) and pushes to `main`
  - Channel routing via secrets: `DISCORD_WEBHOOK_URL` (default fallback), `DISCORD_WEBHOOK_URL_PR` (optional PR channel), `DISCORD_WEBHOOK_URL_MAIN` (optional main channel)
  - Task plan documented in `tasks/discord-git-integration.md`

- **ElevenLabs AI Narration**: Real-time narration of Mars mission events via ElevenLabs TTS
  - `server/app/narrator.py` — narration engine with event filtering (drama weights 1-3), Mistral LLM text generation ("David Attenborough meets space podcaster" persona), ElevenLabs TTS audio conversion, async event batching, and rate limiting
  - `ui/src/components/NarrationPlayer.vue` — audio player with base64 MP3 playback queue, skip/mute controls, pulsing mic icon, responsive layout
  - WebSocket `narration` event type (`{source: "narrator", type: "narration", payload: {text, audio, format}}`) for real-time audio delivery
  - `/narration/toggle` POST and `/narration/status` GET endpoints for runtime control
  - `ELEVENLABS_API_KEY`, `NARRATION_ENABLED`, `NARRATION_VOICE_ID`, `NARRATION_MIN_INTERVAL_SECONDS` config settings
  - Narrator hooks into simulation lifecycle: starts/stops/resets with simulation, feeds on all broadcast events

- **Upgraded TTS model to ElevenLabs v3**: replaced `eleven_flash_v2_5` with `eleven_v3` for premium voice quality with emotional expression
- Updated narrator system prompt to leverage v3 audio tags (`[whispers]`, `[gasps]`, `[laughs]`, `[sighs]`, `[clears throat]`) for dramatic vocal inflection during mission narration

### Fixed

- **Narration text not appearing in UI**: WebSocket event handler matched narrator events on `event.type` instead of `event.name` — both full narration and streaming chunks share `type: "narration"` but differ on `name` (`"narration"` vs `"narration_chunk"`). Fixed in `useWebSocket.js`
- **Voice toggle out of sync with server**: UI initialized `narrationEnabled` to `true` but server defaults to `false`. Fixed to `false` and added `/api/narration/status` fetch on WebSocket connect to sync toggle state

### Changed

- **Always-on text narration**: Mistral `magistral-medium-latest` generates narrative text regardless of ElevenLabs voice toggle — voice is now opt-in only
- **Streaming narration**: text streams to UI via `narration_chunk` WebSocket events using Mistral `chat.stream()`, with typewriter effect in NarrationPlayer
- Audio emotion tags (`[laughs]`, `[sighs]`, etc.) stripped from display text via `_strip_audio_tags()` — kept only for TTS synthesis
- NarrationPlayer toggle relabeled to "Voice ON" / "Voice OFF" to clarify it controls audio only
- Narration model upgraded from `mistral-small-latest` to `magistral-medium-latest`

### Changed

- **EventLog moved below map**: EventLog now renders below the map in the right column instead of below the sidebar, improving layout readability

### Fixed

- Fixed broken `WorldMap.vue` — undefined variable reference that prevented the map from rendering (`fix/worldmap-broken-ref`)

### Changed

- **Rover visibility radius**: per-rover colored dashed circle on the map shows each rover's visibility radius
- **Rovers start at station**: rovers now spawn at station coordinates `(0,0)` and explore outward from there
- Removed `check_ground` from rover actions
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
