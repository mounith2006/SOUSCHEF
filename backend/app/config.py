import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuration settings for STT, Rime TTS, and Conversation Engine."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Rime TTS Config
    rime_api_key: str | None = None
    rime_api_url: str = "https://users.rime.ai/v1/rime-tts"
    rime_model_id: str = "arcana"
    rime_speaker: str = "astra"
    rime_language: str = "eng"
    rime_timeout_seconds: float = 30.0

    # STT Config
    whisper_model: str = "base"
    stt_language: str = "en"

    # LLM Config
    llm_provider: str = "local"  # Safe development default ("local" or "openai")
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()
