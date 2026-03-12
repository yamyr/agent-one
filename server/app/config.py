import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environment
    env: str = "dev"

    # Server
    server_port: int = Field(default=4009, ge=1, le=65535)

    # SurrealDB
    surreal_port: int = Field(default=4002, ge=1, le=65535)
    surreal_url: str = "ws://localhost:4002/rpc"
    surreal_ns: str = "dev"
    surreal_db: str = "mars"
    surreal_user: str = "root"  # SECURITY: override via SURREAL_USER env var in production
    surreal_pass: str = "root"  # SECURITY: override via SURREAL_PASS env var in production

    # CORS
    cors_origins: str = "http://localhost:4089,https://agent-one-production-f066.up.railway.app"

    # Mistral
    mistral_api_key: str = ""
    # Agent backend: "chat_completions" (default) or "agents_api"
    agent_backend: str = "chat_completions"
    # When True, Agents API reasoners reuse conversation threads across turns
    agents_api_persist_threads: bool = True

    # HuggingFace
    hugging_face_read: str = ""
    hugging_face_write: str = ""
    llm_provider: str = "mistral"  # "mistral" or "huggingface"
    huggingface_model: str = "Qwen/Qwen3-32B"
    huggingface_narration_model: str = "Qwen/Qwen3-32B"

    # Simulation timing
    agent_turn_interval_seconds: float = Field(default=0.5, gt=0)
    llm_turn_interval_seconds: float = Field(default=4.0, gt=0)
    drone_turn_interval_seconds: float = Field(default=3.5, gt=0)
    hauler_turn_interval_seconds: float = Field(default=5.0, gt=0)
    event_window_ticks: int = Field(default=50, gt=0)

    # World generation seed (empty = random)
    world_seed: str = ""

    # Active agents (comma-separated)
    active_agents: str = "rover-mistral,rover-2,drone-mistral,station-loop,hauler-mistral,rover-large,rover-medium,rover-codestral,rover-ministral,rover-magistral"

    # Simulation preset (applied on startup after world init)
    preset: str = "default"

    # ElevenLabs narration
    elevenlabs_api_key: str = ""
    narration_enabled: bool = True
    narration_voice_id_male: str = "JBFqnCBsd6RMkjVDRZzb"  # George - Commander Rex
    narration_voice_id_female: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel - Dr. Nova
    narration_model: str = "mistral-medium-latest"
    narration_max_tokens: int = Field(default=350, gt=0)
    narration_temperature: float = Field(default=0.9, ge=0.0, le=2.0)
    elevenlabs_model_id: str = "eleven_v3"
    narration_min_interval_seconds: float = Field(default=5.0, ge=0)

    # Voice command (Voxtral transcription)
    voice_transcription_model: str = "voxtral-mini-latest"
    voice_command_model: str = "mistral-small-latest"

    # Auto-confirm: automatically request confirmation before hazardous moves
    auto_confirm_enabled: bool = True

    # LLM call timeout (seconds)
    llm_call_timeout: float = Field(default=45.0, gt=0)
    # Scripted event timeline: path to JSON file with pre-defined events
    event_script: str = ""

    # Fine-tuning
    training_data_enabled: bool = False
    training_data_dir: str = "./training_data"
    training_snapshot_interval: int = 10
    fine_tuned_agent_model: str = ""
    fine_tuned_narration_model: str = ""


settings = Settings()

# Warn about default SurrealDB credentials in non-dev environments
_cfg_logger = logging.getLogger(__name__)
if settings.env != "dev" and settings.surreal_pass == "root":
    _cfg_logger.warning(
        "SECURITY: SurrealDB is using default credentials (root/root). "
        "Set SURREAL_USER and SURREAL_PASS environment variables for production."
    )
