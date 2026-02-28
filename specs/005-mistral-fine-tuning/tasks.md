# Tasks: Mistral Fine-Tuning Pipeline

## Task 1: Config additions [Phase 1.3]
- **Status**: ✅ completed
- **Depends on**: none
- **Files**: `server/app/config.py`, `server/env.sample`
- **Actions**:
  - Add `training_data_enabled: bool = False` to Settings
  - Add `training_data_dir: str = "training_data"` to Settings
  - Add `fine_tuned_agent_model: str = ""` to Settings
  - Add `fine_tuned_narration_model: str = ""` to Settings
  - Update `env.sample` with new vars

## Task 2: TrainingDataCollector [Phase 1.1]
- **Status**: ✅ completed
- **Depends on**: Task 1
- **Files**: `server/app/training.py` (NEW)
- **Actions**:
  - Create `TrainingDataCollector` class (singleton)
  - `record_agent_interaction(agent_id, agent_type, messages, tools, response)` — writes agent JSONL
  - `record_narration_interaction(messages, response)` — writes narration JSONL
  - JSONL format: `{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "...", "tool_calls": [...]}]}`
  - Include `tool_calls` and `tool` role messages for function calling fine-tuning
  - Thread-safe writes (agents run in executor threads)
  - File naming: `{agent_type}_training_{YYYYMMDD_HHMMSS}.jsonl`
  - Auto-create output directory
  - Guard with `training_data_enabled` check

## Task 3: Hook LLM call sites [Phase 1.2]
- **Status**: ✅ completed
- **Depends on**: Task 2
- **Files**: `server/app/agent.py`, `server/app/station.py`, `server/app/narrator.py`
- **Actions**:
  - In `MistralRoverReasoner.run_turn()`: after LLM response, call `collector.record_agent_interaction()`
  - In `DroneAgent.run_turn()`: same pattern
  - In `StationAgent._call_llm()`: same, capturing all tool calls
  - In `Narrator._generate_text()` and `_generate_text_streaming()`: call `collector.record_narration_interaction()`
  - Import collector lazily to avoid circular imports
  - Minimal code changes — just add recording calls after existing LLM calls

## Task 4: FineTuningManager [Phase 2.1]
- **Status**: ✅ completed
- **Depends on**: Task 1
- **Files**: `server/app/finetuning.py` (NEW)
- **Actions**:
  - Create `FineTuningManager` class
  - `upload_training_data(file_path: str) -> str` — upload JSONL, return file_id
  - `create_job(model, training_file_id, validation_file_id, hyperparameters, suffix) -> dict`
  - `get_job(job_id) -> dict` — get job status
  - `list_jobs() -> list[dict]` — list all jobs
  - `cancel_job(job_id) -> dict` — cancel running job
  - `get_active_models() -> dict` — return current fine-tuned model IDs
  - `activate_model(job_id, target)` — set fine-tuned model as active for agents or narration
  - Lazy Mistral client init (same pattern as agents)
  - Proper error handling for API failures

## Task 5: Model switching [Phase 2.2]
- **Status**: ✅ completed
- **Depends on**: Task 4
- **Files**: `server/app/agent.py`, `server/app/station.py`, `server/app/narrator.py`
- **Actions**:
  - In `MistralRoverReasoner.__init__()`: check `settings.fine_tuned_agent_model`, use if set
  - In `DroneAgent.__init__()`: same
  - In `StationAgent.__init__()`: same
  - In `Narrator._generate_text*()`: check `settings.fine_tuned_narration_model`, use if set
  - No restart required — config is read at each init / call

## Task 6: REST endpoints [Phase 3.1]
- **Status**: ✅ completed
- **Depends on**: Task 4
- **Files**: `server/app/views.py` (extend existing router)
- **Actions**:
  - `GET /fine-tuning/data` — list JSONL files (os.listdir + stat)
  - `POST /fine-tuning/jobs` — create job (body: model, file_path, hyperparams)
  - `GET /fine-tuning/jobs` — list all jobs
  - `GET /fine-tuning/jobs/{job_id}` — get job status
  - `DELETE /fine-tuning/jobs/{job_id}` — cancel job
  - `POST /fine-tuning/jobs/{job_id}/activate` — activate fine-tuned model
  - Use Pydantic models for request/response validation

## Task 7: Wire into app lifespan [Phase 5.1]
- **Status**: ✅ completed
- **Depends on**: Task 2, Task 4, Task 6
- **Files**: `server/app/main.py`
- **Actions**:
  - Initialize TrainingDataCollector singleton in lifespan
  - Initialize FineTuningManager singleton
  - Mount fine-tuning endpoints

## Task 8: Tests [Phase 4]
- **Status**: ✅ completed
- **Depends on**: Tasks 1-7
- **Files**: `server/tests/test_training.py` (NEW), `server/tests/test_finetuning.py` (NEW)
- **Actions**:
  - Test TrainingDataCollector JSONL output format (rover, drone, station, narrator)
  - Test tool-calling message format
  - Test file creation and naming
  - Test enable/disable toggle
  - Test FineTuningManager with mocked Mistral client
  - Test REST endpoints
  - Test config integration

## Task 9: Documentation [Phase 5.2]
- **Status**: ✅ completed
- **Depends on**: Tasks 1-8
- **Files**: `Changelog.md`, `server/env.sample`
- **Actions**:
  - Add Changelog.md entry for fine-tuning feature
  - Verify env.sample has all new vars
  - Add plan markdown file (`tasks/todo.md` equivalent)
