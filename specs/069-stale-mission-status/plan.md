# Implementation Plan: Remove Stale /mission/status Endpoint

**Feature Branch**: `069-stale-mission-status`  
**Created**: 2026-03-01

## Overview

Remove the stale `/mission/status` GET endpoint from `server/app/views.py` and its corresponding test from `server/tests/test_health.py`. This is a pure deletion task with no new code required.

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `server/app/views.py` | Modify | Remove `/mission/status` endpoint (lines 11-14) |
| `server/tests/test_health.py` | Modify | Remove `test_mission_status_returns_idle` test (lines 17-21) |
| `Changelog.md` | Modify | Add entry under [Unreleased] |

## Implementation Steps

1. **Remove endpoint from views.py**: Delete the `@router.get("/mission/status")` decorator and `mission_status()` function
2. **Remove test from test_health.py**: Delete the `test_mission_status_returns_idle` method
3. **Update Changelog.md**: Add removal entry
4. **Verify**: Run ruff format, ruff check, and rut tests

## Risk Assessment

- **Risk**: Low — pure deletion of dead code
- **Rollback**: Revert commit
