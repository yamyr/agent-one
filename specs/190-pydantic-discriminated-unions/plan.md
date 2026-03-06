# Implementation Plan: Pydantic Discriminated Unions for Messages

**Branch**: `190-pydantic-discriminated-unions` | **Date**: 2026-03-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/190-pydantic-discriminated-unions/spec.md`

## Summary

Convert the `Message` dataclass in `server/app/protocol.py` to Pydantic BaseModel with discriminated unions on the `type` field. Five typed subclasses (ActionMessage, EventMessage, CommandMessage, ToolMessage, StreamMessage) replace the untyped Message class. A `parse_message()` factory enables deserialization. All call sites across the codebase are updated. Backward-compatible `to_dict()` output is preserved for WebSocket consumers.

## Technical Context

**Language/Version**: Python 3.14+
**Primary Dependencies**: Pydantic v2 (already available via pydantic-settings), FastAPI, mistralai
**Storage**: N/A (in-memory protocol objects)
**Testing**: pytest (existing test infrastructure with in-memory SurrealDB)
**Target Platform**: Linux/macOS server (FastAPI backend)
**Project Type**: web-service (FastAPI backend + Vue 3 frontend)
**Performance Goals**: N/A (type-safety refactor, no performance-sensitive paths)
**Constraints**: Zero breaking changes to WebSocket serialization format
**Scale/Scope**: ~8 files modified, ~50 call sites updated

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is unconfigured (template placeholders). No gates to evaluate. Proceeding with project-level CLAUDE.md guidelines as governance:
- Simplicity First: Single file modification (protocol.py) with mechanical updates to call sites. No new abstractions beyond what the spec requires.
- Minimal Impact: Only touching message construction and serialization. No changes to world model, agent logic, or WebSocket transport.
- Test coverage: Existing tests updated + new comprehensive tests added.

**Result: PASS** (no violations)

## Project Structure

### Documentation (this feature)

```text
specs/190-pydantic-discriminated-unions/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── protocol.py      # PRIMARY: Pydantic models replace dataclass
│   ├── agent.py          # UPDATE: make_message call sites
│   ├── host.py           # UPDATE: make_message call sites
│   ├── views.py          # UPDATE: make_message call sites
│   ├── main.py           # UPDATE: make_message call sites
│   ├── broadcast.py      # NO CHANGE: receives dict, not Message
│   ├── narrator.py       # NO CHANGE: receives dict, not Message
│   ├── station.py        # NO CHANGE: no direct protocol imports
│   └── world.py          # NO CHANGE: no direct protocol imports
└── tests/
    └── test_protocol.py  # UPDATE: existing + new comprehensive tests
```

**Structure Decision**: Modification-only approach. No new files except test additions. The protocol.py file is the single source of truth for message types.
