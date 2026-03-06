# Data Model: Automatic Request Confirm

**Branch**: `190-auto-request-confirm` | **Date**: 2026-03-06

## No New Entities

This feature does not introduce new data entities. It reuses existing structures:

### Reused Entities

#### Confirmation Request (existing in `host.py`)
```
_pending_confirms[request_id] = {
    agent_id: str          # Agent requesting/blocked by confirmation
    question: str          # Hazard description message
    timeout: int           # Seconds to wait (30)
    event: asyncio.Event   # Signaled when operator responds
    response: bool | None  # True=confirmed, False=denied, None=pending
    tick: int              # World tick at creation
}
```

#### Settings (modified in `config.py`)
```
auto_confirm_enabled: bool = True  # NEW FIELD
```

### Function Signatures (new)

#### `detect_move_hazards()` in `world.py`
```
Input:  agent_id: str, dest_x: int, dest_y: int, move_cost: float
Output: list[str]  # Empty = safe, non-empty = list of hazard descriptions
```

#### `_auto_confirm_gate()` in `agent.py`
```
Input:  host: Host, agent_id: str, action_name: str, params: dict
Output: dict | None  # None = proceed with action, dict = deny result
```

### State Transitions

No new state machines. The existing geyser lifecycle (`idle -> warning -> erupting -> idle`) and storm lifecycle (`clear -> warning -> active -> clear`) are read-only inputs to hazard detection.
