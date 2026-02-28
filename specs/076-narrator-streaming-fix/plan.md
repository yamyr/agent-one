# Implementation Plan: Non-Blocking Narration Streaming

**Branch**: `076-narrator-streaming-fix` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/076-narrator-streaming-fix/spec.md`

## Summary

Fix issue #92 by removing narration-stream processing from the main async event loop, so simulation ticks and websocket traffic remain responsive while narration text streams. Preserve existing narration chunk semantics and add regression tests proving non-blocking behavior.

## Technical Context

**Language/Version**: Python 3.14+ (server)
**Primary Dependencies**: FastAPI, mistralai SDK, asyncio, pytest/rut test runners
**Storage**: N/A (in-memory simulation state)
**Testing**: `uv run pytest tests/`, focused narrator tests, lint via `ruff`
**Target Platform**: Linux/macOS server runtime with websocket clients
**Project Type**: Web application backend service
**Performance Goals**: Narration streaming must not pause simulation tick progression
**Constraints**: No behavior regression in narration chunk event format or ordering
**Scale/Scope**: Targeted server-side fix in narrator loop plus regression tests

## Constitution Check

*GATE: Constitution template is currently unconfigured; no enforceable project-specific gate text present. Applying CLAUDE.md principles manually.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Simplicity First | PASS | Scope limited to narrator streaming path and tests |
| No Laziness | PASS | Root cause addressed (blocking iteration), not symptom |
| Minimal Impact | PASS | No protocol/schema changes planned |
| Verification Before Done | PASS | Add regression tests and run full relevant checks |

## Project Structure

### Documentation (this feature)

```text
specs/076-narrator-streaming-fix/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
server/
├── app/
│   └── narrator.py            # Main fix: non-blocking stream processing
└── tests/
    └── test_narrator.py       # Regression tests for non-blocking behavior

ui/
└── src/
    └── (no required behavior changes expected)
```

**Structure Decision**: Keep fix isolated to backend narration flow and backend tests. No API contract shape changes expected, only runtime behavior improvement.
