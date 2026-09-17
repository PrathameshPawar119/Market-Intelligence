"""NewsAPI and Yahoo Finance headline integrations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from market_intelligence.config.settings import Settings, get_settings
from market_intelligence.tools.http import JsonProvider, ProviderError
from market_intelligence.tools.ratelimit import AsyncRateLimiter

NEWS_API_URL = "https://newsapi.org/v2/everything"
YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
_limiters: dict[int, AsyncRateLimiter] = {}


def _limiter_for(settings: Settings) -> AsyncRateLimiter:
    return _limiters.setdefault(settings.news_requests_per_minute, AsyncRateLimiter(settings.news_requests_per_minute))


def yahoo_symbol(ticker: str, market: str = "NSE") -> str:
    ticker = ticker.upper().strip()
    if "." in ticker:
        return ticker
    return f"{ticker}.NS" if market.upper() == "NSE" else f"{ticker}.BO"


def _iso_date(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    return value if isinstance(value, str) else None


class NewsClient:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider = JsonProvider("news", _limiter_for(self.settings), self.settings, client)

    async def fetch(self, ticker: str, market: str = "NSE", limit: int = 10) -> list[dict[str, Any]]:
        if self.settings.news_api_key:
            return await self._from_newsapi(ticker, market, limit)
        return await self._from_yahoo(ticker, market, limit)

    async def _from_newsapi(self, ticker: str, market: str, limit: int) -> list[dict[str, Any]]:
        payload = await self.provider.get_json(
            NEWS_API_URL,
            params={"q": f'"{ticker.upper()}" AND (stock OR shares OR earnings)', "language": "en", "sortBy": "publishedAt", "pageSize": min(limit, 100), "apiKey": self.settings.news_api_key},
        )
        if payload.get("status") == "error":
            raise ProviderError(f"NewsAPI error: {payload.get('message', 'unknown error')}")
        return [{"headline": article.get("title", ""), "summary": article.get("description") or "", "url": article.get("url"), "published_at": article.get("publishedAt"), "source": (article.get("source") or {}).get("name", "NewsAPI"), "provider": "newsapi"} for article in payload.get("articles", [])[:limit] if article.get("title")]

    async def _from_yahoo(self, ticker: str, market: str, limit: int) -> list[dict[str, Any]]:
        payload = await self.provider.get_json(YAHOO_SEARCH_URL, params={"q": yahoo_symbol(ticker, market), "newsCount": limit, "quotesCount": 1})
        return [{"headline": item.get("title", ""), "summary": item.get("summary") or "", "url": item.get("link"), "published_at": _iso_date(item.get("providerPublishTime")), "source": item.get("publisher", "Yahoo Finance"), "provider": "yahoo_finance"} for item in payload.get("news", [])[:limit] if item.get("title")]


async def get_news(symbol: str, market: str = "NSE") -> list[dict[str, Any]]:
    """Compatibility tool used by existing callers."""
    try:
        return await NewsClient().fetch(symbol, market)
    except ProviderError:
        return [{"headline": f"No live news available for {symbol.upper()}", "source": "mock", "provider": "fallback"}]
