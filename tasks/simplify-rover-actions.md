# Simplify Rover Actions

## Tasks

- [x] Remove `check_ground` from rover tool lists (auto-scanned after each move)
- [x] Remove `charge` from rover tool lists
- [x] Add `charge_rover()` function to `world.py` (station-initiated only)
- [x] Add `CHARGE_ROVER_TOOL` to station agent tools
- [x] Add auto-charge in `agent_loop` when rover arrives at station with low battery
- [x] Update rover prompt: mention auto-charge and return-to-base rule
- [x] Change mission success condition: require delivery to station (not just pickup)
- [x] Enhance mock rover: dig/pickup stones, navigate to station when carrying target stone
- [x] Update all tests: charge tests use `charge_rover()`, mission tests require station delivery
- [x] Verify all 107 tests pass

## Summary of Changes

### `world.py`
- Removed `check_ground` and `charge` from both rover tool definitions
- Updated move tool description to mention auto-scan
- Removed `charge` case from `execute_action()`
- Added `charge_rover()` function for station-initiated charging
- Changed `check_mission_status()`: success now requires target stones delivered to station (rover at station position), not just collected

### `agent.py`
- Updated rover system prompt: auto-charge explanation, return-to-base rule
- Enhanced `MockRoverAgent`: digs/picks up stones at current tile, navigates to station when carrying target stone

### `station.py`
- Added `CHARGE_ROVER_TOOL` definition
- Added `charge_rover` to `STATION_TOOLS` list
- Updated system prompt to mention charging responsibility
- Added `charge_rover` handling in `_execute_tool_calls()`

### `main.py`
- Imported `charge_rover` from world
- Added auto-charge logic in `agent_loop`: charges rover when it arrives at station with < 100% battery

### `test_world.py`
- Rewrote `TestCharge` to use `charge_rover()` instead of `execute_action("charge")`
- Added tests: unknown agent, non-rover rejection, memory recording, charge-not-rover-action
- Updated mission success tests to require station delivery
- Added `test_pickup_away_from_station_no_success` and `test_mission_success_on_move_to_station_with_stone`
