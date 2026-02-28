# World Model

## Grid

20x20 tile grid. Coordinates `(x, y)`, `0 <= x < 20`, `0 <= y < 20`. Origin `(0, 0)` top-left.

## Agent State

Each agent in `WORLD["agents"][id]`:

| Field | Type | Description |
|-------|------|-------------|
| `position` | `[x, y]` | Current tile |
| `battery` | `float` | 0.0–1.0, drains 0.02 per move |
| `mission` | `dict` | `{objective, plan[]}` — will be dynamic from base station |
| `visited` | `[[x, y], ...]` | List of positions the agent has been to. Seeded with starting position. Updated on each successful move (no duplicates). |

## Stones

Stored in `WORLD["stones"]`. Generated at startup by `_generate_stones()`:
- 5–8 stones placed at random grid positions, avoiding agent starting positions
- Each stone: `{"position": [x, y], "type": "core"|"basalt"}`
- Positions are unique (no two stones on the same tile)

## Functions

### `check_ground(agent_id)`

Checks if a stone is present at the agent's current position. Returns `{"stone": {"type": "core"}}` or `{"stone": None}`. Called automatically after every successful move.

### `move_agent(agent_id, x, y)`

Low-level position update. Validates bounds, adjacency, and identity. Does not drain battery or track visited.

### `execute_action(agent_id, action_name, params)`

Engine entry point. Currently supports:

| Action | Params | Effect |
|--------|--------|--------|
| `move` | `{direction: north\|south\|east\|west}` | Move 1 tile, drain battery, append to `visited`, run `check_ground()` |

On successful move, the result dict includes `ground` key with the `check_ground()` output.

### `get_snapshot()`

Returns a deep copy of the entire `WORLD` dict (grid, agents, stones).

## Turn Flow

```
agent.run_turn()        → single-shot LLM call, returns {thinking, action}
agent_loop (main.py)    → engine: execute_action() → broadcast events + snapshot
                           if stone found → broadcast "check" event
```

Agents return action dicts. They never mutate world directly.

Mock agent prefers unvisited neighbor tiles. LLM agent receives visited count and unvisited neighbors in sensor readings.
