# Task: Simplify Rover Actions

## Changes

### 1. Remove `check_ground` as an explicit action
- [x] Remove from rover tools list in `world.py` WORLD init
- [x] Remove from `execute_action` dispatcher (if present)
- [x] Keep `check_ground()` function — it's used internally for auto-scan after moves
- [x] Update tests: remove tests that call check_ground as an action
- [x] Update agent context to clarify ground is auto-scanned

### 2. Make `charge` a station-only action
- [x] Remove `charge` from rover tools list in `world.py` WORLD init
- [x] Add `charge_rover` tool to station's Mistral tools in `station.py`
- [x] Station calls charge when rover is co-located
- [x] Keep `_execute_charge` in world.py (station invokes it)
- [x] Update `execute_action` to accept charge from station context
- [x] Update tests for new charge flow
- [x] Update rover agent context to say "return to station for charging"

### 3. Carry over .kiro files
- [x] Commit .kiro steering files

### 4. Verify
- [x] All tests pass
- [x] Update Changelog.md
