# Tasks: Fix DroneLoop Charge Event Name

**Feature**: Fix DroneLoop Charge Event Name  
**Branch**: `001-fix-charge-event`  
**Generated**: 2026-03-01

## Phase 1: Core Fix

- [x] T001 Change `name="charge_rover"` to `name="charge_agent"` in RoverLoop at `server/app/agent.py` L838
- [x] T002 Change `name="charge_rover"` to `name="charge_agent"` in DroneLoop at `server/app/agent.py` L925

## Phase 2: Narrator Update

- [x] T003 Update drama weight key from `"charge_rover"` to `"charge_agent"` in `server/app/narrator.py` L37
- [x] T004 Update event name check from `"charge_rover"` to `"charge_agent"` in `server/app/narrator.py` L161
- [x] T005 Update narration text from `"charged a rover"` to `"charged an agent"` in `server/app/narrator.py` L164

## Phase 3: Test Updates

- [x] T006 Update `test_charge_rover_event` → `test_charge_agent_event` in `server/tests/test_narrator.py`

## Phase 4: Verification

- [x] T007 Run `uv run ruff check app/ tests/` — pre-existing warnings only
- [x] T008 Run `uv run ruff format --check app/ tests/` — all files pass
- [x] T009 Run `uv run rut tests/` — 287 tests passed
- [x] T010 Update `Changelog.md` with the fix
