"""Tool-calling market research agent.

The LLM chooses a subset of the three read-only tools.  Tool calls from one
assistant turn are executed concurrently, so a model requesting news and a
quote does not serialize two network round trips.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from market_intelligence.config.settings import get_settings
from market_intelligence.llm.models import get_chat_model
from market_intelligence.observability import invoke_llm
from market_intelligence.tools.market import compute_technicals, get_market_data
from market_intelligence.tools.news import get_news

ToolFn = Callable[[str, str], Awaitable[Any]]


class MarketToolAgent:
    def __init__(self, llm: Any | None = None, *, news: ToolFn = get_news, price: ToolFn = get_market_data) -> None:
        self.llm = llm
        self._tools: dict[str, ToolFn] = {"get_news": news, "get_price": price}

    async def decide(self, ticker: str, market: str) -> list[str]:
        """Ask a configured tool-capable LLM, with a safe deterministic fallback."""
        settings = get_settings()
        llm = self.llm or (get_chat_model() if settings.enable_llm and settings.has_configured_provider else None)
        if llm is None:
            return ["get_news", "get_price", "get_technicals"]
        # Bind named schemas so an LLM can select tools natively.  A simple
        # mock only needs ``ainvoke`` and is supported for unit tests too.
        model = llm
        if hasattr(llm, "bind_tools"):
            from langchain_core.tools import StructuredTool

            async def news_tool(ticker: str, market: str = "NSE") -> object:
                return await self._tools["get_news"](ticker, market)

            async def price_tool(ticker: str, market: str = "NSE") -> object:
                return await self._tools["get_price"](ticker, market)

            async def technicals_tool(ticker: str, market: str = "NSE") -> object:
                history = await self._tools["get_price"](ticker, market)
                return compute_technicals(history.get("closes", []))

            model = llm.bind_tools([
                StructuredTool.from_function(coroutine=news_tool, name="get_news", description="Get the latest ticker headlines."),
                StructuredTool.from_function(coroutine=price_tool, name="get_price", description="Get current price and daily closing history."),
                StructuredTool.from_function(coroutine=technicals_tool, name="get_technicals", description="Get SMA, RSI and price trend."),
            ])
        try:
            response = await invoke_llm(
                model,
                f"For {ticker} on {market}, choose needed read-only tools from "
                "get_news, get_price, get_technicals. Return tool calls only.",
                ticker,
            )
        except Exception:  # noqa: BLE001 - provider exceptions vary by SDK
            # Providers occasionally fail before research starts.  The
            # read-only default plan is still sound and keeps signals flowing.
            return ["get_news", "get_price", "get_technicals"]
        calls = [call.get("name") for call in getattr(response, "tool_calls", []) if call.get("name") in {"get_news", "get_price", "get_technicals"}]
        return calls or ["get_news", "get_price", "get_technicals"]

    async def run(self, ticker: str, market: str) -> dict[str, Any]:
        calls = await self.decide(ticker, market)
        # Technicals are computed from the same price history rather than
        # issuing an avoidable second quote request.
        network_calls = [name for name in calls if name in self._tools]
        values = await asyncio.gather(*(self._tools[name](ticker, market) for name in network_calls), return_exceptions=True)
        result: dict[str, Any] = {"tool_calls": calls}
        for name, value in zip(network_calls, values, strict=True):
            if isinstance(value, Exception):
                result.setdefault("errors", []).append(f"{name}: {value}")
            else:
                result[name] = value
        price = result.get("get_price")
        if "get_technicals" in calls:
            result["get_technicals"] = compute_technicals(price.get("closes", [])) if price else None
        return result
