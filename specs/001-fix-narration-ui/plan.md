# Implementation Plan: Fix Narration Text Display & Voice Toggle

**Branch**: `001-fix-narration-ui` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fix-narration-ui/spec.md`

## Summary

Fix 4 bugs preventing narration text from appearing in the UI and the voice toggle from working. The WebSocket event routing uses wrong field names for matching narrator events, and the voice toggle state is never synced from the server on page load.

## Technical Context

**Language/Version**: Python 3.12+ (server), JavaScript/Vue 3 (UI)
**Primary Dependencies**: FastAPI, Vue 3, Vite, Mistral AI SDK, ElevenLabs SDK
**Storage**: N/A (in-memory state only)
**Testing**: `rut` (unittest runner), ESLint
**Target Platform**: Web browser (desktop/tablet/mobile)
**Project Type**: Web application (full-stack)
**Performance Goals**: Narration text visible within 5s of events
**Constraints**: No new dependencies; minimal code changes (bug fix only)
**Scale/Scope**: 4 targeted fixes across 2 UI files

## Constitution Check

*GATE: Constitution is unconfigured (blank template). No gates to evaluate. Proceeding.*

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-narration-ui/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (trivial — no unknowns)
├── data-model.md        # Phase 1 output (event schemas)
├── contracts/           # Phase 1 output (WebSocket event contracts)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── narrator.py         # No changes needed (server-side is correct)
│   └── main.py             # No changes needed (endpoints exist and work)
└── tests/
    └── test_narrator.py    # Verify existing tests still pass

ui/
└── src/
    ├── App.vue                          # Fix: init narrationEnabled=false, fetch status on connect
    ├── composables/useWebSocket.js      # Fix: match on event.name instead of event.type
    └── components/NarrationPlayer.vue   # No changes needed (component logic is correct)
```

**Structure Decision**: Existing web application structure. Changes limited to 2 UI files only.

## Complexity Tracking

No violations — this is a minimal bug fix with 4 targeted line changes.
