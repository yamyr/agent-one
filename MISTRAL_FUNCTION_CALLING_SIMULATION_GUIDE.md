# Mistral Function Calling for the Station + Rover Simulation

## Purpose
This guide explains how to expose simulation actions as Mistral function-calling tools so an LLM-driven agent can reason, pick actions, call tools, and advance the world state.

This is written for the current simulation engine in:
- `server/app/sim/engine.py`
- `server/app/sim/world_factory.py`

## What to use from Mistral Function Calling
Based on Mistral docs (`/capabilities/function_calling`):
- Pass tool definitions via `tools=[...]` (JSON schema per function).
- Use `tool_choice`:
  - `"auto"`: model decides whether to call tools.
  - `"any"`: force at least one tool call.
  - `"none"`: disable tools.
- Use `parallel_tool_calls` to allow/disallow parallel tool calls.
- Execute tool calls in your backend, append tool outputs as `role="tool"` messages, and continue until the model returns a final assistant response (no `tool_calls`).

## Recommended setup for this simulation
- Use `parallel_tool_calls=False`.
- Reason: simulation actions mutate shared world state and should remain sequential/deterministic.
- Use one coordinator loop: `observe -> call model -> execute tool(s) -> feed tool result -> repeat`.

## Tool set by entity

### Rover tools
- `rover_move(to_x: integer, to_y: integer)` -> wraps `engine.step({"kind":"move","to":(to_x,to_y)})`
- `rover_dig()` -> wraps `engine.step({"kind":"dig"})`
- `rover_pickup()` -> wraps `engine.step({"kind":"pickup"})`
- `rover_wait()` -> wraps `engine.step({"kind":"wait"})`

### Station tools
- `station_charge_rover()` -> wraps `engine.step({"kind":"charge"})`
- `station_get_telemetry()` -> returns rover battery, distance to station, mission progress

### World/coordination read tools
- `get_rover_observation()` -> `engine.get_observation("rover")`
- `get_station_observation()` -> `engine.get_observation("station")`
- `get_legal_actions()` -> `engine.get_legal_actions()`
- `get_world_state()` -> `engine.get_world_state_dict()`

## Example tool schema (Mistral)
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "rover_move",
            "description": "Move rover by one orthogonal cell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_x": {"type": "integer", "description": "Target X coordinate."},
                    "to_y": {"type": "integer", "description": "Target Y coordinate."},
                },
                "required": ["to_x", "to_y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rover_dig",
            "description": "Dig at the rover's current position.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
```

## Coordinator loop template
```python
import json
from mistralai import Mistral

client = Mistral(api_key=MISTRAL_API_KEY)
messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# map tool names to local callables
names_to_functions = {
    "rover_move": rover_move,
    "rover_dig": rover_dig,
    "rover_pickup": rover_pickup,
    "rover_wait": rover_wait,
    "station_charge_rover": station_charge_rover,
    "get_rover_observation": get_rover_observation,
    "get_station_observation": get_station_observation,
    "get_legal_actions": get_legal_actions,
    "get_world_state": get_world_state,
}

messages.append({"role": "user", "content": user_instruction})

response = client.chat.complete(
    model="mistral-large-latest",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    parallel_tool_calls=False,
)
messages.append(response.choices[0].message)

while response.choices[0].message.tool_calls:
    for tc in response.choices[0].message.tool_calls:
        fn_name = tc.function.name
        fn_args = json.loads(tc.function.arguments or "{}")
        fn_result = names_to_functions[fn_name](**fn_args)

        messages.append({
            "role": "tool",
            "name": fn_name,
            "content": json.dumps(fn_result),
            "tool_call_id": tc.id,
        })

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        parallel_tool_calls=False,
    )
    messages.append(response.choices[0].message)

final_text = response.choices[0].message.content
```

## Implementation notes for this repo
- Keep tool wrappers thin and deterministic: wrappers should only call `SimulationEngine` methods and return structured JSON.
- Always return `accepted`, `events`, `terminal_status`, and key telemetry from action tools.
- Treat invalid actions as normal tool results (not exceptions) so the model can self-correct.
- Start each turn by giving the model `get_rover_observation()` + `get_legal_actions()` context.

## Suggested next code module (when implementation starts)
Create `server/app/sim/mistral_tools.py` containing:
- tool JSON schemas
- names-to-functions registry
- tool execution helper (`execute_tool_call(tool_call, engine)`)

## Sources
- Mistral Function Calling docs: https://docs.mistral.ai/capabilities/function_calling/
- Mistral Agents Function Calling docs: https://docs.mistral.ai/agents/function_calling/
