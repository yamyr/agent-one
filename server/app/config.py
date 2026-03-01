from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environment
    env: str = "dev"

    # Server
    server_port: int = 4009

    # SurrealDB
    surreal_port: int = 4002
    surreal_url: str = "ws://localhost:4002/rpc"
    surreal_ns: str = "dev"
    surreal_db: str = "mars"
    surreal_user: str = "root"
    surreal_pass: str = "root"

    # CORS
    cors_origins: str = "http://localhost:4089"

    # Mistral
    mistral_api_key: str = ""

    # Simulation timing
    agent_turn_interval_seconds: float = 0.5
    llm_turn_interval_seconds: float = 3.0

    # World generation seed (empty = random)
    world_seed: str = ""

    # Active agents (comma-separated: "rover-mistral,drone-mistral")
    active_agents: str = "rover-mistral,rover-2,drone-mistral"

    # ElevenLabs narration
    elevenlabs_api_key: str = ""
    narration_enabled: bool = False
    narration_voice_id_male: str = "JBFqnCBsd6RMkjVDRZzb"  # George - Commander Rex
    narration_voice_id_female: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel - Dr. Nova
    narration_model: str = "mistral-medium-latest"
    narration_min_interval_seconds: float = 5.0

    # Voxtral voice commander
    voxtral_model: str = "voxtral-mini-latest"
    voice_command_enabled: bool = True

settings = Settings()
