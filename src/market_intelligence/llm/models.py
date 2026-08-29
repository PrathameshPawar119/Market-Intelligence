from __future__ import annotations

from functools import lru_cache
from typing import Any

from market_intelligence.config.settings import get_settings


@lru_cache
def get_chat_model() -> Any:
    """Return the shared configured chat model instance for the active provider."""

    settings = get_settings()
    provider = settings.model_provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
        )

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
        )

    raise ValueError(
        "Unsupported model provider configured. Use one of: openai, gemini, claude."
    )
