from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    spoonacular_api_key: str | None = None
    spoonacular_api_url: str = "https://api.spoonacular.com"
    spoonacular_timeout_seconds: float = 15.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
