# HuggingFace Integration Plan

## Goal
Add HuggingFace Inference API as an alternative LLM provider alongside Mistral. Agents (Rover, Drone, Station, Narrator) should be able to use models hosted on HuggingFace via config-driven provider selection.

## Design Decision
Config-driven provider switching within existing class structure. Both SDKs use nearly identical OpenAI-compatible tool call formats, so we create parallel reasoner/loop classes for HuggingFace and register them as new agent variants.

## Tasks

### 1. Config & Dependencies
- [x] Create plan file
- [x] Add HuggingFace config fields to `config.py`:
  - `hugging_face_read: str = ""` — read API key
  - `hugging_face_write: str = ""` — write API key
  - `llm_provider: str = "mistral"` — provider selection
  - `huggingface_model: str = "Qwen/Qwen2.5-72B-Instruct"` — default HF model
  - `huggingface_narration_model: str = "Qwen/Qwen2.5-72B-Instruct"` — HF narration model
- [x] Add `huggingface-hub>=0.25.0` to `pyproject.toml` dependencies
- [x] Add HuggingFace env vars to `env.sample`

### 2. Agent Implementation (`agent.py`)
- [x] Add `HuggingFaceRoverReasoner` class (mirrors `MistralRoverReasoner` with HF `InferenceClient`)
- [x] Add `HuggingFaceDroneAgent` class (mirrors `DroneAgent` with HF `InferenceClient`)
- [x] Add `RoverHuggingFaceLoop` class (wires `HuggingFaceRoverReasoner` to `RoverLoop`)
- [x] Add `DroneHuggingFaceLoop` class (wires `HuggingFaceDroneAgent` to `DroneLoop`)
- [x] Error handling: `HfHubHTTPError`, `InferenceTimeoutError` instead of `SDKError`

### 3. Station Implementation (`station.py`)
- [x] Add `_get_hf_client()` method to `StationAgent`
- [x] Modify `_get_client()` to select provider based on `settings.llm_provider`
- [x] Update `_call_llm()` to use correct API method per provider
- [x] Add HuggingFace error handling

### 4. Narrator Implementation (`narrator.py`)
- [x] Add `_get_huggingface()` method to `Narrator`
- [x] Modify `_generate_text()` to support HuggingFace non-streaming
- [x] Modify `_generate_text_streaming()` to support HuggingFace streaming
- [x] Provider selection based on `settings.llm_provider`

### 5. Agent Registration (`main.py`)
- [x] Import new loop classes
- [x] Add `"rover-huggingface"` and `"drone-huggingface"` to `AGENT_MAP`

### 6. Tests
- [x] Test HuggingFace config fields load correctly
- [x] Test `HuggingFaceRoverReasoner` with mocked `InferenceClient`
- [x] Test `HuggingFaceDroneAgent` with mocked `InferenceClient`
- [x] Test `StationAgent` with HuggingFace provider
- [x] Test `Narrator` with HuggingFace provider (streaming + non-streaming)
- [x] Test fallback behavior on HuggingFace errors

### 7. Documentation & Finalization
- [x] Update `Changelog.md`
- [x] Run `uv run rut tests/` — all 340 tests pass
- [x] Run `uv run ruff check` — no lint errors
- [x] Run `uv run ruff format` — formatting OK
- [x] Commit with co-author trailer
- [x] Push and create PR

## SDK Comparison

| Feature | Mistral | HuggingFace |
|---------|---------|-------------|
| Client | `Mistral(api_key=...)` | `InferenceClient(token=..., provider="auto")` |
| Chat | `client.chat.complete(...)` | `client.chat_completion(...)` |
| Stream | `client.chat.stream(...)` | `client.chat_completion(..., stream=True)` |
| Stream chunk | `event.data.choices[0].delta.content` | `chunk.choices[0].delta.content` |
| Tool format | OpenAI-compatible JSON | OpenAI-compatible JSON (identical) |
| Errors | `SDKError` | `HfHubHTTPError`, `InferenceTimeoutError` |
| Auth env var | `MISTRAL_API_KEY` | `HUGGING_FACE_READ` / `HUGGING_FACE_WRITE` |
