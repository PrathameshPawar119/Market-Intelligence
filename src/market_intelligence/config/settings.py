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

    # Market data.  Keys are optional: Yahoo Finance remains a useful public
    # fallback for development, while Alpha Vantage and NewsAPI are preferred
    # whenever credentials have been configured.
    news_api_key: Optional[str] = None  # noqa: UP045
    alpha_vantage_api_key: Optional[str] = None  # noqa: UP045
    request_timeout_seconds: float = 8.0
    provider_max_retries: int = 2
    provider_backoff_seconds: float = 0.25
    news_requests_per_minute: int = 20
    market_requests_per_minute: int = 20
    cache_ttl_seconds: int = 300
    max_parallel_tickers: int = 5
    # Disabled by default to prevent an accidental local .env key from
    # generating cost.  Enable explicitly in a deployed signal worker.
    enable_llm: bool = False
    requests_per_minute_per_user: int = 10
    redis_url: str | None = None
    daily_cost_alert_usd: float = 10.0
    input_token_cost_per_million_usd: float = 0.15
    output_token_cost_per_million_usd: float = 0.60

    # These are deliberately optional.  The application emits structured
    # traces locally even when a hosted Langfuse deployment is not configured.
    langfuse_public_key: Optional[str] = None  # noqa: UP045
    langfuse_secret_key: Optional[str] = None  # noqa: UP045
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def active_api_key(self) -> str | None:
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
