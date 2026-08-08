from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app runs with zero configuration.
    # Point this at Postgres (see docker-compose.yml) for the "real" stack.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'signal.db'}"

    # If unset, the LLM client falls back to a deterministic simulator so the
    # whole pipeline and eval suite still run end to end. See app/llm/client.py.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
