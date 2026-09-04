from functools import lru_cache

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    whisper_model: str = "base"

    whisper_language: str = "en"

    whisper_timeout_seconds: float = 120.0

    frontend_origin: str = "*"


@lru_cache(maxsize=1)
def get_settings() -> Settings:

    return Settings()