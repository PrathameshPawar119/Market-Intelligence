from market_intelligence.config.settings import Settings
from market_intelligence.llm.models import get_chat_model


def test_get_chat_model_uses_configured_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "market_intelligence.config.settings.get_settings",
        lambda: Settings(
            model_provider="gemini",
            gemini_api_key="gemini-test-key",
            gemini_model="gemini-2.0-flash",
            openai_api_key=None,
            anthropic_api_key=None,
        ),
    )
    get_chat_model.cache_clear()

    model = get_chat_model()

    assert model.__class__.__name__ == "ChatGoogleGenerativeAI"


def test_get_chat_model_defaults_to_openai(monkeypatch) -> None:
    monkeypatch.setattr(
        "market_intelligence.config.settings.get_settings",
        lambda: Settings(
            model_provider="openai",
            openai_api_key="openai-test-key",
            openai_model="gpt-4o-mini",
            gemini_api_key=None,
            anthropic_api_key=None,
        ),
    )
    get_chat_model.cache_clear()

    model = get_chat_model()

    assert model.__class__.__name__ == "ChatOpenAI"
