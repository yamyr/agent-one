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
    surreal_user: str = "root"
    surreal_pass: str = "root"

    # CORS
    cors_origins: str = "http://localhost:4089"

    # Mistral
    mistral_api_key: str = ""

    # HuggingFace
    hugging_face_read: str = ""
    hugging_face_write: str = ""
    llm_provider: str = "mistral"  # "mistral" or "huggingface"
    huggingface_model: str = "Qwen/Qwen2.5-72B-Instruct"
    huggingface_narration_model: str = "Qwen/Qwen2.5-72B-Instruct"

    # Simulation timing
    agent_turn_interval_seconds: float = Field(default=0.5, gt=0)
    llm_turn_interval_seconds: float = Field(default=3.0, gt=0)
    drone_turn_interval_seconds: float = Field(default=2.0, gt=0)

    # World generation seed (empty = random)
    world_seed: str = ""

    # Active agents (comma-separated: "rover-mistral,drone-mistral")
    active_agents: str = "rover-mistral,rover-2,drone-mistral,station-loop"

    # ElevenLabs narration
    elevenlabs_api_key: str = ""
    narration_enabled: bool = False
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

    # Fine-tuning
    training_data_enabled: bool = False
    training_data_dir: str = "./training_data"
    training_snapshot_interval: int = 10
    fine_tuned_agent_model: str = ""
    fine_tuned_narration_model: str = ""


settings = Settings()
