# Implementation Plan: Control Buttons & Narration Enablement

**Branch**: `165-control-buttons-narration` | **Date**: 2026-03-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/165-control-buttons-narration/spec.md`

## Summary

All control buttons (PAUSE, RESUME, RESET, ABORT, Voice ON/OFF) and the entire narration pipeline (Mistral LLM + ElevenLabs TTS) are already fully implemented and wired end-to-end. The only issues are two config/state defaults that prevent the system from working correctly out of the box:

1. **Server config**: `narration_enabled` defaulted to `False`, silently blocking the entire narrator pipeline even when API keys were present.
2. **UI state sync**: `narrationEnabled` defaulted to `ref(true)` while the server defaulted to `false`, creating a 3-second mismatch where the UI showed "Voice ON" but narration was actually off.

This plan covers flipping both defaults and adding test coverage for the control endpoints.

## Technical Context

**Language/Version**: Python 3.14+ (server), JavaScript/Vue 3 (UI)  
**Primary Dependencies**: FastAPI, Vue 3, Vite 7, Mistral AI SDK, ElevenLabs SDK  
**Storage**: SurrealDB (port 4002)  
**Testing**: `rut` (unittest-based runner), in-memory SurrealDB via `conftest.py`  
**Target Platform**: Web (desktop + responsive)  
**Project Type**: Web application (FastAPI backend + Vue 3 SPA)  
**Performance Goals**: N/A — config changes only, no runtime impact  
**Constraints**: Changes must not break existing tests (`rut tests/`)  
**Scale/Scope**: 4 files changed (2 one-line fixes, 1 new test file, 1 changelog entry)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ No new dependencies introduced
- ✅ No architectural changes — config defaults only
- ✅ No new API endpoints — all endpoints already exist
- ✅ No breaking changes to existing behavior
- ✅ Co-authored-by trailer required on all commits

## Project Structure

### Documentation (this feature)

```text
specs/165-control-buttons-narration/
├── spec.md              # Feature specification (completed)
└── plan.md              # This file
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── config.py           # CHANGE: narration_enabled default False → True
│   ├── main.py             # NO CHANGE: endpoints already exist
│   ├── narrator.py         # NO CHANGE: 674-line narrator fully implemented
│   ├── views.py            # NO CHANGE: /ws endpoint already wired
│   └── ...
└── tests/
    └── test_control_buttons.py  # NEW: test suite for control endpoints

ui/
└── src/
    └── pages/
        └── SimulationPage.vue   # CHANGE: narrationEnabled ref(true) → ref(false)

Changelog.md                     # CHANGE: add 0.7.0 entry
```

**Structure Decision**: Existing web application structure. No new directories or modules needed — all changes are in existing files except one new test file.

## Implementation Details

### Change 1: Server Config Default (server/app/config.py)

**What**: Change `narration_enabled: bool = False` → `narration_enabled: bool = True`

**Why**: The narrator code (narrator.py, 674 lines) is fully implemented with Mistral LLM streaming text generation and ElevenLabs TTS. It checks `settings.narration_enabled` before processing events. With the default at `False`, the entire pipeline is silently blocked even when the operator has set `ELEVENLABS_API_KEY`. Flipping to `True` means narration activates automatically when API keys are present, matching the user's "go all in" request.

**Risk**: None — the narrator already gracefully degrades when `ELEVENLABS_API_KEY` is missing (text-only mode) or when the key is invalid (catches exceptions, logs, continues).

**Line change**: Single line, `narration_enabled: bool = True`

### Change 2: UI State Sync (ui/src/pages/SimulationPage.vue)

**What**: Change `const narrationEnabled = ref(true)` → `const narrationEnabled = ref(false)`

**Why**: The UI should start conservative (narration OFF) and sync the actual state from the server via `GET /api/narration/status` on WebSocket connect. Previously, the UI defaulted to `ref(true)` while the server defaulted to `false`, creating a 3-second window where the toggle showed "Voice ON" but narration was actually disabled server-side. By defaulting the UI to `false`, the toggle correctly shows OFF until the server confirms the real state.

**Risk**: None — the existing `fetch('/api/narration/status')` call on WebSocket connect already updates `narrationEnabled.value` from the server response. This change only affects the brief moment before that fetch completes.

**Line change**: Single line, `const narrationEnabled = ref(false)`

### Change 3: Test Suite (server/tests/test_control_buttons.py)

**What**: New test file with comprehensive coverage for all simulation control endpoints and narration toggle.

**Tests to include**:
- `test_pause_returns_ok` — POST /pause returns 200 with success payload
- `test_resume_returns_ok` — POST /resume returns 200 with success payload
- `test_reset_returns_ok` — POST /reset returns 200 with success payload
- `test_abort_returns_ok` — POST /abort returns 200 with success payload
- `test_narration_toggle_on` — POST /narration/toggle with `enabled=true` returns 200
- `test_narration_toggle_off` — POST /narration/toggle with `enabled=false` returns 200
- `test_narration_status` — GET /narration/status returns current enabled state
- `test_pause_resume_cycle` — Pause then resume in sequence, verify both succeed
- `test_reset_after_pause` — Reset while paused, verify clean state
- `test_narration_toggle_rapid` — Rapid on/off/on toggling, verify last-write-wins

**Test framework**: `rut` (unittest-based), uses `CaseWithDB` base class from existing test infrastructure.

### Change 4: Changelog (Changelog.md)

**What**: Add `[0.7.0]` section documenting the config fix, UI sync fix, and new tests.

**Sections**:
- **Features**: narration enabled by default, UI state sync fix
- **Bug Fixes**: narration toggle initial state mismatch
- **Tests**: control button endpoint test suite
- **Errors Identified & Prevented**: document the state mismatch pattern to prevent recurrence

## Complexity Tracking

No complexity violations. All changes are minimal config/default fixes with one new test file. No new abstractions, patterns, or dependencies introduced.

## Verification Checklist

- [ ] `narration_enabled` defaults to `True` in `server/app/config.py`
- [ ] `narrationEnabled` defaults to `ref(false)` in `ui/src/pages/SimulationPage.vue`
- [ ] `server/tests/test_control_buttons.py` exists with 10+ tests
- [ ] All tests pass: `rut tests/` (run from `server/`)
- [ ] Linter passes: `ruff check app/ tests/` (run from `server/`)
- [ ] No LSP diagnostics/errors on changed files
- [ ] Changelog.md has 0.7.0 entry
- [ ] Commit includes `Co-Authored-By: agent-one team <agent-one@yanok.ai>`
