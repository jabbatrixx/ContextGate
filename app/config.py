"""Centralized application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    database_url: str = "postgresql+asyncpg://contextgate:contextgate@localhost:5432/contextgate"
    profiles_path: str = "profiles.yaml"
    api_key: str = ""
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once per process)."""
    return Settings()
