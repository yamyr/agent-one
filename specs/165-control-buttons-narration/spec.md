# Feature Specification: Control Buttons & Narration Enablement

**Feature Branch**: `165-control-buttons-narration`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: User description: "Get the buttons working properly — RESET, PAUSE, ABORT, Voice ON/OFF. Re-enable ElevenLabs TTS and Mistral narration, go all in."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PAUSE / RESUME Simulation (Priority: P1)

As an operator, I can pause the simulation to freeze all agent activity and resume it to continue from the same state — so I can observe the world without it changing.

**Why this priority**: Pause/Resume is the most fundamental control. Without it, the operator cannot stop the simulation to inspect state or discuss findings.

**Independent Test**: Click PAUSE → verify no new ticks/events arrive via WebSocket. Click RESUME → verify ticks resume and events flow again.

**Acceptance Scenarios**:

1. **Given** simulation is running, **When** operator clicks PAUSE, **Then** the simulation loop stops, no new ticks are processed, and the button label changes to RESUME
2. **Given** simulation is paused, **When** operator clicks RESUME, **Then** the simulation loop resumes from where it stopped, new events flow, and the button label changes to PAUSE
3. **Given** simulation is paused, **When** operator checks the timer, **Then** elapsed time is frozen and does not increment

---

### User Story 2 - RESET Simulation (Priority: P1)

As an operator, I can reset the simulation to return all agents, world state, and the timer to their initial configuration — so I can start a fresh run.

**Why this priority**: Reset enables rapid iteration. Without it, the operator must restart the server to try again.

**Independent Test**: Start simulation, let it run for a few ticks, click RESET → verify all agents return to starting positions, battery is full, timer resets to 0, and event log is cleared.

**Acceptance Scenarios**:

1. **Given** simulation is running or paused, **When** operator clicks RESET, **Then** world state resets (agents at origin, full battery, no active missions), timer resets to 0:00, and simulation is paused
2. **Given** simulation has been reset, **When** operator clicks RESUME, **Then** simulation starts cleanly from tick 0

---

### User Story 3 - ABORT Mission (Priority: P2)

As an operator, I can abort the current mission to halt all agent activity and mark the mission as failed — so I can end a bad run without full reset.

**Why this priority**: Abort is a safety valve. It's less common than pause/reset but critical when missions go sideways.

**Independent Test**: Start a mission, click ABORT → verify mission status changes to "aborted", agents stop acting, but world state is preserved (not reset).

**Acceptance Scenarios**:

1. **Given** a mission is running (`mission.status === 'running'`), **When** operator clicks ABORT, **Then** mission status becomes "aborted", agents stop, and the ABORT button disappears
2. **Given** no mission is running, **Then** the ABORT button is not visible (this is correct existing behavior)

---

### User Story 4 - Voice ON/OFF Toggle (Narration) (Priority: P1)

As an operator, I can toggle voice narration on and off — to enable AI-generated commentary with text-to-speech during the simulation.

**Why this priority**: This is the headline feature. The user explicitly asked to "go all in" on narration with ElevenLabs + Mistral.

**Independent Test**: Toggle Voice ON → verify narration text appears in NarrationPlayer and audio plays via ElevenLabs TTS. Toggle Voice OFF → verify narration stops and no new audio chunks arrive.

**Acceptance Scenarios**:

1. **Given** narration is OFF (server default), **When** operator toggles Voice ON, **Then** server `narration_enabled` becomes `true`, narrator starts processing simulation events, and text + audio stream to the UI
2. **Given** narration is ON, **When** operator toggles Voice OFF, **Then** server `narration_enabled` becomes `false`, narrator stops generating text and TTS, and the UI reflects the OFF state
3. **Given** narration is ON and a simulation event occurs, **Then** the narrator generates text via Mistral LLM and synthesizes speech via ElevenLabs TTS, streamed to the NarrationPlayer component
4. **Given** the UI connects to the server, **When** WebSocket connection is established, **Then** the UI fetches the current narration status from the server and syncs its toggle state before displaying controls

---

### User Story 5 - Narration System Fully Enabled (Priority: P1)

As a system, when narration is turned on, the full pipeline works: Mistral LLM generates commentary text → ElevenLabs TTS converts to speech → audio streams to the UI.

**Why this priority**: The user explicitly said "go all in" — this means the entire narration pipeline must be functional, not just the toggle.

**Independent Test**: Enable narration, run simulation, verify narration_chunk WebSocket events arrive with both text and audio data.

**Acceptance Scenarios**:

1. **Given** `ELEVENLABS_API_KEY` is set in .env and `NARRATION_ENABLED=true`, **When** the server starts, **Then** the narrator initializes with ElevenLabs client and is ready to generate TTS
2. **Given** narration is enabled and a significant simulation event occurs, **When** the narrator processes it, **Then** Mistral generates dual-narrator dialogue (Commander Rex + Dr. Nova) with emotion tags
3. **Given** ElevenLabs API key is NOT set, **When** narration is enabled, **Then** text narration still works but TTS is gracefully skipped (no crashes)

---

### Edge Cases

- What happens when ElevenLabs API key is invalid or expired? → Narrator should catch the error, log it, and continue with text-only narration
- What happens when user toggles narration rapidly (ON/OFF/ON)? → Server should handle state changes atomically, last-write-wins
- What happens when RESET is clicked while narration is playing? → Audio queue should be cleared, narrator should reset its state
- What happens when PAUSE is clicked while narration audio is mid-playback? → Audio should continue playing current chunk but no new chunks should be generated
- What happens on first WebSocket connect with 3-second delay? → UI should sync narration state from server BEFORE enabling any narration UI elements

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Server config MUST default `narration_enabled` to `True` (changed from `False`) so narration is available when API keys are present
- **FR-002**: UI MUST sync narration toggle state from server on WebSocket connect, before displaying controls
- **FR-003**: UI narration toggle (`Voice ON/OFF`) MUST call `POST /api/narration/toggle` and update local state based on server response
- **FR-004**: PAUSE button MUST call `POST /api/pause` and freeze simulation ticks + timer
- **FR-005**: RESUME button MUST call `POST /api/resume` and unfreeze simulation ticks + timer
- **FR-006**: RESET button MUST call `POST /api/reset` and return world to initial state with timer at 0
- **FR-007**: ABORT button MUST call `POST /api/abort` and mark current mission as aborted
- **FR-008**: ABORT button MUST only be visible when `mission.status === 'running'`
- **FR-009**: Narrator MUST use Mistral LLM (`mistral-medium-latest`) for text generation with dual-narrator dialogue format
- **FR-010**: Narrator MUST use ElevenLabs TTS (`eleven_v3`) for speech synthesis when API key is available
- **FR-011**: Narrator MUST gracefully degrade to text-only when ElevenLabs API key is missing or invalid
- **FR-012**: All control button endpoints MUST return appropriate JSON responses indicating success/failure
- **FR-013**: UI MUST NOT show stale narration state — state must be fetched from server on every reconnect

### Key Entities

- **NarrationState**: Server-side boolean (`narration_enabled`) controlling whether the narrator processes events
- **SimulationState**: Running/paused/stopped — controlled by pause/resume/reset/abort actions
- **Host**: Central simulation controller that manages pause state, elapsed time, and agent lifecycle

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 4 control buttons (PAUSE, RESUME, RESET, ABORT) correctly call their backend endpoints and produce the expected state change
- **SC-002**: Voice ON/OFF toggle correctly enables/disables narration pipeline end-to-end (Mistral text → ElevenLabs TTS → WebSocket → UI audio)
- **SC-003**: UI narration state matches server state within 1 second of WebSocket connection
- **SC-004**: No console errors or unhandled promise rejections in the UI when using any control button
- **SC-005**: All existing tests pass (`rut tests/`) with no regressions
- **SC-006**: Linter passes (`ruff check app/ tests/`) with no new warnings
