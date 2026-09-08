"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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
    llm_provider: Literal["openai", "gemini"] = "openai"
    llm_model: str = "gpt-5-mini"
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    extraction_batch_char_limit: int = Field(default=50_000, ge=1)
    extraction_batch_page_limit: int = Field(default=8, ge=1)
    evidence_fuzzy_threshold: float = Field(default=92.0, ge=0.0, le=100.0)
    fiscal_year_start_month: int = Field(default=4, ge=1, le=12)
    max_upload_bytes: int = Field(default=100 * 1024 * 1024, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for normal application use."""

    return Settings()
