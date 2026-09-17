import httpx
import pytest

from market_intelligence.config.settings import Settings
from market_intelligence.tools.market import MarketClient
from market_intelligence.tools.news import NewsClient


@pytest.mark.asyncio
async def test_newsapi_headlines_are_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "newsapi.org"
        return httpx.Response(200, json={"status": "ok", "articles": [{"title": "INFY profit growth", "description": "Quarterly result", "url": "https://example.test/a", "publishedAt": "2026-01-01T00:00:00Z", "source": {"name": "Example"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        headlines = await NewsClient(Settings(news_api_key="test-key"), client).fetch("INFY")

    assert headlines == [{"headline": "INFY profit growth", "summary": "Quarterly result", "url": "https://example.test/a", "published_at": "2026-01-01T00:00:00Z", "source": "Example", "provider": "newsapi"}]


@pytest.mark.asyncio
async def test_alpha_vantage_price_history_is_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["function"] == "TIME_SERIES_DAILY"
        return httpx.Response(200, json={"Time Series (Daily)": {"2026-01-02": {"4. close": "100.5"}, "2026-01-03": {"4. close": "102.0"}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        history = await MarketClient(Settings(alpha_vantage_api_key="test-key"), client).price_history("INFY")

    assert history["price"] == 102.0
    assert history["closes"] == [100.5, 102.0]
