from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_provider: Literal["openai", "gemini", "claude"] = "openai"

    openai_api_key: Optional[str] = None  # noqa: UP045
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: Optional[str] = None  # noqa: UP045
    gemini_model: str = "gemini-2.0-flash"

    anthropic_api_key: Optional[str] = None  # noqa: UP045
    anthropic_model: str = "claude-3-5-sonnet-latest"

    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def active_api_key(self) -> Optional[str]:
        provider_to_key = {
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "claude": self.anthropic_api_key,
        }
        return provider_to_key.get(self.model_provider.lower())

    @property
    def active_model_name(self) -> str:
        provider_to_model = {
            "openai": self.openai_model,
            "gemini": self.gemini_model,
            "claude": self.anthropic_model,
        }
        return provider_to_model.get(self.model_provider.lower(), self.openai_model)

    @property
    def has_configured_provider(self) -> bool:
        return bool(self.active_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
