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

    # World generation seed (empty = random)
    world_seed: str = ""


settings = Settings()
