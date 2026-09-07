"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by the API and background pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FKL_",
        extra="ignore",
    )

    app_name: str = "Fact Knowledge Layer"
    environment: str = "development"
    database_url: str = Field(default="sqlite:///./fact_knowledge_layer.db")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for normal application use."""

    return Settings()
