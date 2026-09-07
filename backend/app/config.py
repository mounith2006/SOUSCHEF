import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Ensure .env is explicitly loaded from backend/ or project root
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_backend_dir, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)
else:
    load_dotenv(override=True)


class Settings(BaseSettings):
    """Configuration for the voice pipeline."""

    model_config = SettingsConfigDict(
        env_file=_env_path if os.path.exists(_env_path) else ".env",
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

    # LLM configuration
    llm_provider: str = "local"
    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
