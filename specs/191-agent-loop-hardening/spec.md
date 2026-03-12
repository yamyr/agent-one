# 191 — Agent Loop Hardening

## Problem

Six bugs in `server/app/agent.py` cause agent crashes or incorrect behavior during LLM reasoning loops:

1. **Missing tool whitelist entries**: `drop_item` and `request_confirm` are defined in `ROVER_TOOLS` but not in the run_turn() whitelist for MistralRoverReasoner or HuggingFaceRoverReasoner — LLM calling these tools triggers "unknown tool" warning and crashes the agent.

2. **RuntimeError not caught**: All `run_turn()` methods raise `RuntimeError` when the LLM returns no tool call, but except clauses in Mistral and HuggingFace variants don't catch it — the error propagates and crashes the agent loop instead of graceful fallback.

3. **json.JSONDecodeError not caught**: `json.loads(tc.function.arguments)` can fail with malformed LLM output, crashing the agent instead of falling back.

4. **Drone intel relay hardcoded to rover-mistral**: `DroneLoop.tick()` only sends high-concentration scan results to `"rover-mistral"`, ignoring all other active rovers.

5. **HaulerMistralLoop default agent_id mismatch**: Default is `"hauler-1"` but the world model creates `"hauler-mistral"`.

6. **Dead HaulerReasoner class**: 157 lines of dead code with obsolete `pickup_cargo` tool references and `"hauler-1"` default — fully superseded by `HaulerAgent`.

## Solution

- Add `drop_item`, `request_confirm` to both rover whitelist tuples
- Add `RuntimeError`, `json.JSONDecodeError` to all 5 except clauses
- Replace hardcoded drone relay with loop over `self._world.get_agents()` filtered by `type == "rover"`
- Fix default from `"hauler-1"` to `"hauler-mistral"`
- Delete dead `HaulerReasoner` class and `MistralHaulerReasoner` alias; keep `HaulerReasoner = HaulerAgent` backward-compat alias

## Files Changed

| File | Change |
|------|--------|
| `server/app/agent.py` | All 6 fixes |
| `server/tests/test_agent_loop_hardening.py` | 26 new tests |
| `server/tests/test_huggingface.py` | Updated 1 test for new fallback behavior |
