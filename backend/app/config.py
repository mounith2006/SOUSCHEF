from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the narrow, server-side Rime integration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rime_api_key: str | None = None
    rime_api_url: str = "https://users.rime.ai/v1/rime-tts"
    rime_model_id: str = "arcana"
    rime_speaker: str = "astra"
    rime_language: str = "eng"
    rime_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
