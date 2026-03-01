# 006 — World-Data Fine-Tuning Pipeline

## Goal

Capture all LLM interactions (system prompt, user message, assistant response + tool calls) from rover, drone, station, and narrator agents during simulation runs. Record world-state context alongside each interaction as JSONL training data. Track data across simulation "generations" (runs). Upload to Mistral API and manage fine-tuning jobs. Allow switching agents to use fine-tuned models.

## Architecture

### New Modules

1. **`server/app/training.py`** — `TrainingDataCollector` singleton
   - Thread-safe (agents run via `asyncio.to_thread`)
   - Appends JSONL samples per agent type: `rover_training_<session>.jsonl`, `drone_training_<session>.jsonl`, etc.
   - Records: system prompt, user message, assistant response (content + tool_calls), generation_id, tick
   - Enabled/disabled via `settings.training_data_enabled`

2. **`server/app/finetuning.py`** — `FineTuningManager` singleton
   - Wraps Mistral SDK: file upload, job create/get/list/cancel, model activation
   - Lazy client initialization (only when needed)
   - Model switching: stores fine-tuned model IDs on settings object

### Modified Modules

3. **`server/app/config.py`** — Add settings:
   - `training_data_enabled: bool = False`
   - `training_data_dir: str = "./training_data"`
   - `fine_tuned_agent_model: str = ""` (overrides agent model when set)
   - `fine_tuned_narration_model: str = ""` (overrides narration model when set)

4. **`server/app/world.py`** — Add `generation_id: int` to WORLD dict, increment on `reset_world()`

5. **`server/app/agent.py`** — Hook `MistralRoverReasoner.run_turn()` and `DroneAgent.run_turn()`:
   - After LLM response, call `collector.record_agent_interaction()`
   - Read model from `settings.fine_tuned_agent_model` if set (model switching)

6. **`server/app/station.py`** — Hook `StationAgent._call_llm()`:
   - After LLM response, call `collector.record_agent_interaction()`
   - Model switching support

7. **`server/app/narrator.py`** — Hook `_generate_text()` and `_generate_text_streaming()`:
   - After text generation, call `collector.record_narration_interaction()`
   - Model switching support

8. **`server/app/views.py`** — Add 7 REST endpoints:
   - `GET /fine-tuning/status` — Config status
   - `GET /fine-tuning/data` — List JSONL files
   - `POST /fine-tuning/jobs` — Upload data + create job
   - `GET /fine-tuning/jobs` — List all jobs
   - `GET /fine-tuning/jobs/{job_id}` — Get job details
   - `DELETE /fine-tuning/jobs/{job_id}` — Cancel job
   - `POST /fine-tuning/jobs/{job_id}/activate` — Activate fine-tuned model

9. **`server/app/main.py`** — No changes needed (collector is module-level singleton)

### New Test Files

10. **`server/tests/test_training.py`** — Tests for TrainingDataCollector
11. **`server/tests/test_finetuning.py`** — Tests for FineTuningManager

## JSONL Training Data Format

```jsonl
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "...", "tool_calls": [{"id": "...", "type": "function", "function": {"name": "move", "arguments": "{\"direction\": \"north\"}"}}]}, {"role": "tool", "content": "ok", "tool_call_id": "...", "name": "move"}]}
```

## LLM Call Sites to Hook (5 total)

| # | Agent | File:Line | Method | Model |
|---|-------|-----------|--------|-------|
| 1 | Rover | agent.py:366-370 | `MistralRoverReasoner.run_turn()` | mistral-small-latest |
| 2 | Drone | agent.py:670-674 | `DroneAgent.run_turn()` | mistral-small-latest |
| 3 | Station | station.py:180-184 | `StationAgent._call_llm()` | mistral-small-latest |
| 4 | Narrator (sync) | narrator.py:534-542 | `Narrator._generate_text()` | mistral-medium-latest |
| 5 | Narrator (stream) | narrator.py:558-566 | `Narrator._generate_text_streaming()` | mistral-medium-latest |

## Tasks

- [x] 1. Add config settings (`config.py`)
- [x] 2. Add `generation_id` to WORLD dict (`world.py`)
- [x] 3. Create `training.py` — TrainingDataCollector
- [x] 4. Create `finetuning.py` — FineTuningManager
- [x] 5. Hook rover LLM call (`agent.py`)
- [x] 6. Hook drone LLM call (`agent.py`)
- [x] 7. Hook station LLM call (`station.py`)
- [x] 8. Hook narrator sync LLM call (`narrator.py`)
- [x] 9. Hook narrator streaming LLM call (`narrator.py`)
- [x] 10. Add model switching to rover/drone/station/narrator
- [x] 11. Add REST endpoints (`views.py`)
- [x] 12. Write `test_training.py` (8 tests)
- [x] 13. Write `test_finetuning.py` (15 tests)
- [x] 14. Run tests + lint + format (326 passed)
- [ ] 15. Update `Changelog.md`
- [ ] 16. Create PR

## Constraints

- Thread-safe: agents run in `ThreadPoolExecutor` via `asyncio.to_thread()`
- Lazy imports to avoid circular dependencies
- `mistralai>=1.0.0` already in pyproject.toml
- Magistral models do NOT support fine-tuning — only base models
- Fine-tuneable models: `mistral-small-latest`, `open-mistral-nemo`, `mistral-large-latest`
- Python 3.14+, Ruff line-length=100
- Tests use `rut` (NOT pytest)
