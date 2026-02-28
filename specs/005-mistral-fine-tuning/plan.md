# Plan: Mistral Fine-Tuning Pipeline

## Phase 1: Training Data Collection Infrastructure

**Goal**: Intercept all LLM calls and persist them as JSONL training data.

### 1.1 TrainingDataCollector class (`server/app/training.py`)
- Singleton pattern (like Broadcaster)
- `record_interaction(agent_type, messages, tools, response, model)` method
- Converts LLM request/response pairs to Mistral fine-tuning JSONL format
- Handles both tool-calling format (agents) and text completion format (narrator)
- Writes to `{training_data_dir}/{agent_type}_training_{timestamp}.jsonl`
- Thread-safe (agents run in ThreadPoolExecutor)
- Configurable via `training_data_enabled` setting

### 1.2 Hook into existing LLM call sites
- `MistralRoverReasoner.run_turn()` — after `client.chat.complete()`, record full interaction
- `DroneAgent.run_turn()` — same pattern
- `StationAgent._call_llm()` — same pattern, but captures multiple tool calls
- `Narrator._generate_text()` / `_generate_text_streaming()` — capture narration prompt/response

### 1.3 Config additions (`server/app/config.py`)
- `training_data_enabled: bool = False`
- `training_data_dir: str = "training_data"`
- `fine_tuned_agent_model: str = ""` (empty = use default)
- `fine_tuned_narration_model: str = ""` (empty = use default)

## Phase 2: Fine-Tuning Manager

**Goal**: Manage the full fine-tuning lifecycle via Mistral API.

### 2.1 FineTuningManager class (`server/app/finetuning.py`)
- `upload_training_data(file_path) -> file_id` — Upload JSONL to Mistral Files API
- `create_job(model, training_file_id, validation_file_id, hyperparameters, suffix) -> job` — Create fine-tuning job
- `get_job(job_id) -> job_status` — Poll job status
- `list_jobs() -> [jobs]` — List all jobs
- `cancel_job(job_id)` — Cancel a running job
- `activate_model(job_id)` — Set fine-tuned model as active (updates config)
- Uses `client.files.upload()`, `client.fine_tuning.jobs.create/get/list/cancel()`

### 2.2 Model switching
- When `fine_tuned_agent_model` is set in config, agents use that model ID
- When `fine_tuned_narration_model` is set, narrator uses that model ID
- Modify `MistralRoverReasoner.__init__`, `DroneAgent.__init__`, `StationAgent.__init__`, and `Narrator._generate_text*()` to check for fine-tuned model override

## Phase 3: REST API

**Goal**: Expose fine-tuning management via HTTP endpoints.

### 3.1 Router (`server/app/views.py` or new router)
- `POST /fine-tuning/export` — Export collected training data summary
- `GET /fine-tuning/data` — List available JSONL files with sizes and sample counts
- `POST /fine-tuning/jobs` — Create a fine-tuning job (body: model, file_path, hyperparameters)
- `GET /fine-tuning/jobs` — List all fine-tuning jobs
- `GET /fine-tuning/jobs/{job_id}` — Get specific job status
- `DELETE /fine-tuning/jobs/{job_id}` — Cancel a job
- `POST /fine-tuning/jobs/{job_id}/activate` — Activate fine-tuned model

## Phase 4: Testing

**Goal**: Comprehensive test coverage for all new code.

### 4.1 Test TrainingDataCollector
- Test JSONL format output for each agent type (rover, drone, station, narrator)
- Test tool-calling format correctness
- Test file rotation and thread safety
- Test enable/disable toggle
- Test with mock LLM responses matching real agent patterns

### 4.2 Test FineTuningManager
- Test file upload (mocked Mistral client)
- Test job create/get/list/cancel (mocked)
- Test model activation
- Test error handling (API failures, invalid files)

### 4.3 Test REST endpoints
- Test all endpoints with mocked manager
- Test validation (missing params, invalid job IDs)

## Phase 5: Integration & Documentation

### 5.1 Integration
- Wire TrainingDataCollector into app lifespan (main.py)
- Wire FineTuningManager as singleton
- Mount fine-tuning router

### 5.2 Documentation
- Update Changelog.md
- Update CLAUDE.md with fine-tuning module docs
- Add env.sample entries for new config vars

## Verification Criteria

- [ ] Training data JSONL output matches Mistral's expected format exactly
- [ ] All 4 LLM call sites (rover, drone, station, narrator) correctly captured
- [ ] Fine-tuning API calls use correct SDK methods and parameters
- [ ] Model switching works without restart
- [ ] All tests pass (`rut tests/`)
- [ ] Ruff lint/format clean
- [ ] No type errors or suppression
