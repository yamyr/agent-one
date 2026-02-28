# Tasks: Remove Stale /mission/status Endpoint

**Feature Branch**: `069-stale-mission-status`  
**Created**: 2026-03-01

## Tasks

- [x] T1: Remove `@router.get("/mission/status")` endpoint from `server/app/views.py`
- [x] T2: Remove `test_mission_status_returns_idle` test from `server/tests/test_health.py`
- [x] T3: Update `Changelog.md` with removal entry
- [x] T4: Run `uv run ruff format app/ tests/ && uv run ruff check app/ tests/` — verify pass
- [x] T5: Run `uv run rut tests/` — verify all tests pass
- [x] T6: Commit, push, create PR
