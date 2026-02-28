# Research: Fix Version Drift

**Feature**: 005-fix-version-drift  
**Date**: 2026-02-28

## Research Summary

No unknowns to resolve. This is a deterministic one-line fix.

## Decisions

### D-001: Version String Source of Truth

- **Decision**: `server/pyproject.toml` is the canonical version source. `main.py` must match.
- **Rationale**: `pyproject.toml` is the standard Python packaging metadata file and is already at `0.2.0`.
- **Alternatives considered**:
  - Read version from `pyproject.toml` at runtime using `importlib.metadata` — rejected as over-engineering for a hackathon project.
  - Use a shared `__version__` module — rejected for same reason.
