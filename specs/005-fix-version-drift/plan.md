# Implementation Plan: Fix Version Drift

**Branch**: `005-fix-version-drift` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-fix-version-drift/spec.md`

## Summary

Fix version string mismatch: `server/app/main.py` declares `version="0.1.0"` in the FastAPI constructor while `server/pyproject.toml` correctly declares `version = "0.2.0"`. The fix is a single-line change to align `main.py` with the canonical version.

## Technical Context

**Language/Version**: Python 3.14+  
**Primary Dependencies**: FastAPI  
**Storage**: N/A  
**Testing**: rut (unittest runner)  
**Target Platform**: Linux server / macOS dev  
**Project Type**: web-service  
**Performance Goals**: N/A (metadata-only change)  
**Constraints**: None  
**Scale/Scope**: Single line change in one file

## Constitution Check

*GATE: Pass — constitution is not yet configured for this project. No violations.*

## Project Structure

### Documentation (this feature)

```text
specs/005-fix-version-drift/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (trivial — no unknowns)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
server/
├── app/
│   └── main.py          # Line 62: version="0.1.0" → version="0.2.0"
└── pyproject.toml       # Already correct at 0.2.0 (no change)
```

**Structure Decision**: No structural changes. Single file edit in existing codebase.

## Phase 0: Research

No unknowns to research. The fix is deterministic:
- **Decision**: Change `version="0.1.0"` to `version="0.2.0"` in `server/app/main.py`
- **Rationale**: `pyproject.toml` is the source of truth; `main.py` must match
- **Alternatives considered**: Reading version from `pyproject.toml` at runtime (rejected — over-engineered for a hackathon project)

## Phase 1: Design

No data model changes. No contract changes. No new dependencies.

### Change Details

| File | Line | Current | Target |
|------|------|---------|--------|
| `server/app/main.py` | 62 | `version="0.1.0"` | `version="0.2.0"` |
