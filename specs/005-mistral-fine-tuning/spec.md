# Spec: Mistral Fine-Tuning Pipeline

## Overview

Add a training data collection and fine-tuning pipeline to the Mars simulation server. The system intercepts all LLM interactions (rover, drone, station, narrator) during simulation runs, exports them as JSONL training data, and uses the Mistral Fine-Tuning API to create domain-adapted models that improve agent performance over time.

## Problem Statement

Our Mars simulation agents use generic Mistral models (`mistral-small-latest`, `mistral-medium-latest`). As the simulation runs, agents generate high-quality reasoning + tool-call sequences that are lost when the session ends. Fine-tuning on this accumulated data would produce specialized models that:

1. Better understand our custom tool schemas (move, dig, analyze, scan, notify, etc.)
2. Make more efficient decisions in the Mars environment context
3. Reduce hallucinated tool arguments and invalid actions
4. Produce more contextually appropriate narration

## Constraints

### Model Compatibility (CRITICAL)

**Magistral models (`magistral-medium-latest`, `magistral-small-latest`) do NOT support fine-tuning** via the Mistral API. The supported fine-tuneable models are:

| Model ID | Use Case |
|----------|----------|
| `mistral-small-latest` | Agent reasoning (rover, drone, station) — cost-effective |
| `mistral-large-latest` | High-quality agent reasoning — premium |
| `open-mistral-nemo` | Alternative lightweight option |
| `codestral-latest` | Code-focused tasks |
| `mistral-medium-latest` | Narration generation |

**Decision**: Fine-tune `mistral-small-latest` for agents and `mistral-medium-latest` for narration (these are our current production models).

### Data Format

Mistral fine-tuning requires JSONL with `{"messages": [...]}` per line. Each message has `role` (system/user/assistant/tool) and `content`. Function calling fine-tuning is supported — `tool_calls` and `tool` role messages can be included.

### API Constraints

- Max training file: 512 MB
- Min: ~10 training examples (recommended: 100+)
- Fine-tuned model ID format: `ft:<base-model>:<suffix>:<date>:<id>`
- Job lifecycle: QUEUED → VALIDATED → RUNNING → SUCCEEDED/FAILED
- Hyperparameters: training_steps, learning_rate (default 1e-4), weight_decay, warmup_fraction, epochs, seq_len

## Architecture

### Components

1. **TrainingDataCollector** — Middleware that intercepts LLM calls and writes JSONL
   - Hooks into `MistralRoverReasoner.run_turn()`, `DroneAgent.run_turn()`, `StationAgent._call_llm()`, `Narrator._generate_text*()`
   - Writes to configurable output directory as timestamped JSONL files
   - Separates agent training data from narration training data (different base models)

2. **FineTuningManager** — Manages the Mistral fine-tuning lifecycle
   - Upload JSONL files to Mistral Files API
   - Create, monitor, and cancel fine-tuning jobs
   - Track job status and fine-tuned model IDs
   - Switch active models to fine-tuned versions

3. **REST Endpoints** — Management API
   - `POST /fine-tuning/export` — Trigger JSONL export from collected data
   - `GET /fine-tuning/data` — List available training data files
   - `POST /fine-tuning/jobs` — Create a fine-tuning job
   - `GET /fine-tuning/jobs` — List jobs
   - `GET /fine-tuning/jobs/{id}` — Get job status
   - `DELETE /fine-tuning/jobs/{id}` — Cancel a job
   - `POST /fine-tuning/jobs/{id}/activate` — Switch to fine-tuned model

4. **Config** — New settings in `config.py`
   - `training_data_enabled: bool` — Toggle data collection
   - `training_data_dir: str` — Output directory for JSONL files
   - `fine_tuned_agent_model: str` — Override agent model with fine-tuned ID
   - `fine_tuned_narration_model: str` — Override narration model with fine-tuned ID

### Data Flow

```
Simulation Run
    │
    ├─ Rover LLM call ──────┐
    ├─ Drone LLM call ──────┤
    ├─ Station LLM call ────┼──→ TrainingDataCollector ──→ agent_training_YYYYMMDD_HHMMSS.jsonl
    └─ Narrator LLM call ───┘                           ──→ narration_training_YYYYMMDD_HHMMSS.jsonl
                                                              │
                                                              ▼
                                                    FineTuningManager
                                                         │
                                                    ┌────┘└────┐
                                                    ▼          ▼
                                              Upload to    Create Job
                                              Mistral      (auto_start)
                                              Files API         │
                                                                ▼
                                                          Monitor Job
                                                                │
                                                                ▼
                                                          On SUCCESS:
                                                          Store ft model ID
                                                          ──→ Switch active model
```

## Non-Goals

- Real-time/online learning during simulation (fine-tuning is batch, offline)
- Custom training infrastructure (we use Mistral's hosted fine-tuning)
- Evaluation framework (rely on Mistral's built-in validation loss tracking)
- UI for fine-tuning management (REST API only for now)
