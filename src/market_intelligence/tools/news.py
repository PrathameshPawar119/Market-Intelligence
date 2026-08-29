from typing import Any


async def get_news(symbol: str, market: str) -> list[dict[str, Any]]:
    """Return news in a stable shape for a future news provider integration."""

    # TODO: Replace mock data with a news API.
    return [
        {
            "headline": f"No live news loaded for {symbol.upper()} ({market.upper()})",
            "source": "mock",
        }
    ]
