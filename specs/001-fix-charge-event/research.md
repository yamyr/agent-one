# Research: Fix DroneLoop Charge Event Name

## Decision: Use `charge_agent` as the generic event name

**Decision**: Use `"charge_agent"` for all charge broadcast events from both RoverLoop and DroneLoop.

**Rationale**: `charge_agent()` is the canonical function name in `world.py`. `charge_rover` is just a backward-compat alias. Using a generic name future-proofs for new agent types.

**Alternatives rejected**: `"charge_drone"` for DroneLoop (doesn't scale), per-type event names (more complex).
