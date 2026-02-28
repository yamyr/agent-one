# Task: Rover Mistral Turn Cadence and Movement Reliability

## Plan

- [x] Make agent turn interval configurable from settings
- [x] Set default turn interval to 0.5s for faster rover turns
- [x] Add fallback behavior when RoverAgent LLM call fails or returns no tool action
- [x] Update changelog with the runtime behavior changes
- [x] Verify with lint and focused server tests

## Review Notes

- Turn cadence now comes from `settings.agent_turn_interval_seconds` and starts at 0.5s by default.
- `RoverAgent.run_turn()` now degrades to `MockRoverAgent` behavior on LLM failures or empty/invalid tool output, preventing idle turns.
- Verification: `uv run ruff check app tests`, `uv run ruff format --check app tests`, `uv run python -m unittest tests.test_agent -v`.
