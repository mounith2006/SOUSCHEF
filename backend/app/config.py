from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the voice pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Whisper STT
    whisper_model: str = "small"
    whisper_language: str = "en"
    whisper_timeout_seconds: float = 120.0

    # Frontend
    frontend_origin: str = "*"

    # Rime TTS
    rime_api_key: str | None = None
    rime_api_url: str = "https://users.rime.ai/v1/rime-tts"
    rime_model_id: str = "arcana"
    rime_speaker: str = "astra"
    rime_language: str = "eng"
    rime_timeout_seconds: float = 30.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()