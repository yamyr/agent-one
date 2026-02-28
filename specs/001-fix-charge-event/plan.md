# Implementation Plan: Fix DroneLoop Charge Event Name

**Branch**: `001-fix-charge-event` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)

## Summary

Fix semantically incorrect event name in DroneLoop and RoverLoop charge broadcasts. Both agent loops emit `name="charge_rover"` when broadcasting charge events, but the correct generic name should be `"charge_agent"`. The narrator is also updated to recognize the new event name.

## Technical Context

**Language/Version**: Python 3.14+  
**Primary Dependencies**: FastAPI, mistralai SDK  
**Testing**: rut (unittest runner), ruff (linter/formatter)  
**Project Type**: Web service (multi-agent simulation)

## Change Inventory

| File | Change | Lines |
|------|--------|-------|
| `server/app/agent.py` L838 | `"charge_rover"` → `"charge_agent"` (RoverLoop) | 1 |
| `server/app/agent.py` L925 | `"charge_rover"` → `"charge_agent"` (DroneLoop) | 1 |
| `server/app/narrator.py` L37 | `"charge_rover": 2` → `"charge_agent": 2` | 1 |
| `server/app/narrator.py` L161 | `name == "charge_rover"` → `name == "charge_agent"` | 1 |
| `server/app/narrator.py` L164 | `"charged a rover"` → `"charged an agent"` | 1 |
| `server/tests/test_narrator.py` L114 | test method name update | 1 |
| `server/tests/test_narrator.py` L118 | `"charge_rover"` → `"charge_agent"` | 1 |
