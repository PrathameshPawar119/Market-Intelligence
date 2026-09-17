import asyncio

import pytest

from market_intelligence.agents.tool_agent import MarketToolAgent


@pytest.mark.asyncio
async def test_tool_agent_executes_independent_tools_in_parallel() -> None:
    called: list[str] = []

    async def news(ticker: str, market: str) -> list[dict]:
        called.append("get_news")
        await asyncio.sleep(0.03)
        return [{"headline": "growth"}]

    async def price(ticker: str, market: str) -> dict:
        called.append("get_price")
        await asyncio.sleep(0.03)
        return {"closes": [100.0, 101.0]}

    agent = MarketToolAgent(news=news, price=price)
    result = await agent.run("INFY", "NSE")

    assert result["tool_calls"] == ["get_news", "get_price", "get_technicals"]
    assert set(called) == {"get_news", "get_price"}
    assert result["get_technicals"]["return_1d_pct"] == 1.0
