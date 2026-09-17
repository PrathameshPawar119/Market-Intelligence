"""Alpha Vantage and Yahoo Finance price/technical-data integrations."""

from __future__ import annotations

from statistics import fmean
from typing import Any

import httpx

from market_intelligence.config.settings import Settings, get_settings
from market_intelligence.tools.http import JsonProvider, ProviderError
from market_intelligence.tools.news import yahoo_symbol
from market_intelligence.tools.ratelimit import AsyncRateLimiter

ALPHA_URL = "https://www.alphavantage.co/query"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_limiters: dict[int, AsyncRateLimiter] = {}


def _limiter_for(settings: Settings) -> AsyncRateLimiter:
    return _limiters.setdefault(settings.market_requests_per_minute, AsyncRateLimiter(settings.market_requests_per_minute))


class MarketClient:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider = JsonProvider("market data", _limiter_for(self.settings), self.settings, client)

    async def price_history(self, ticker: str, market: str = "NSE", days: int = 90) -> dict[str, Any]:
        if self.settings.alpha_vantage_api_key:
            return await self._from_alpha_vantage(ticker, market)
        return await self._from_yahoo(ticker, market, days)

    async def _from_alpha_vantage(self, ticker: str, market: str) -> dict[str, Any]:
        symbol = yahoo_symbol(ticker, market)
        payload = await self.provider.get_json(ALPHA_URL, params={"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact", "apikey": self.settings.alpha_vantage_api_key})
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict):
            raise ProviderError(payload.get("Note") or payload.get("Information") or "Alpha Vantage returned no daily series")
        rows = sorted(series.items())[-90:]
        closes = [float(row["4. close"]) for _, row in rows]
        return {"symbol": ticker.upper(), "market": market.upper(), "price": closes[-1], "closes": closes, "currency": "INR", "source": "alpha_vantage"}

    async def _from_yahoo(self, ticker: str, market: str, days: int) -> dict[str, Any]:
        symbol = yahoo_symbol(ticker, market)
        payload = await self.provider.get_json(YAHOO_CHART_URL.format(symbol=symbol), params={"range": f"{max(days, 30)}d", "interval": "1d"})
        result = (payload.get("chart") or {}).get("result") or []
        if not result:
            error = (payload.get("chart") or {}).get("error") or {}
            raise ProviderError(error.get("description", "Yahoo Finance returned no price data"))
        result0 = result[0]
        closes = [float(value) for value in ((result0.get("indicators") or {}).get("quote") or [{}])[0].get("close", []) if value is not None]
        if not closes:
            raise ProviderError("Yahoo Finance returned an empty close series")
        meta = result0.get("meta") or {}
        return {"symbol": ticker.upper(), "market": market.upper(), "price": closes[-1], "closes": closes, "currency": meta.get("currency", "INR"), "source": "yahoo_finance"}


def compute_technicals(closes: list[float]) -> dict[str, float | str | None]:
    if len(closes) < 2:
        return {"sma_20": None, "sma_50": None, "rsi_14": None, "trend": "unknown", "return_1d_pct": None}
    sma20 = fmean(closes[-20:]) if len(closes) >= 20 else fmean(closes)
    sma50 = fmean(closes[-50:]) if len(closes) >= 50 else fmean(closes)
    window = closes[-15:]
    gains = [max(window[i] - window[i - 1], 0.0) for i in range(1, len(window))]
    losses = [max(window[i - 1] - window[i], 0.0) for i in range(1, len(window))]
    avg_loss = fmean(losses)
    rsi = 100.0 if avg_loss == 0 else round(100 - (100 / (1 + fmean(gains) / avg_loss)), 2)
    return {"sma_20": round(sma20, 2), "sma_50": round(sma50, 2), "rsi_14": rsi, "trend": "bullish" if closes[-1] >= sma20 >= sma50 else "bearish", "return_1d_pct": round((closes[-1] / closes[-2] - 1) * 100, 3)}


async def get_price(symbol: str, market: str = "NSE") -> dict[str, Any]:
    return await MarketClient().price_history(symbol, market)


async def get_technicals(symbol: str, market: str = "NSE") -> dict[str, Any]:
    history = await get_price(symbol, market)
    return compute_technicals(history["closes"])


async def get_market_data(symbol: str, market: str) -> dict[str, Any]:
    """Compatibility method. It returns a stable result even in offline CI."""
    try:
        return await get_price(symbol, market)
    except ProviderError:
        return {"symbol": symbol.upper(), "market": market.upper(), "price": None, "closes": [], "currency": "INR" if market.upper() == "NSE" else None, "source": "mock"}
