"""First graph node: collect independent price and news evidence concurrently."""

from __future__ import annotations

from market_intelligence.agents.tool_agent import MarketToolAgent
from market_intelligence.graph.state import MarketIntelligenceState
from market_intelligence.rag import LocalRagIndex, default_rag_index
from market_intelligence.tools.market import compute_technicals


class ResearchAgent:
    def __init__(self, rag_index: LocalRagIndex | None = None, tool_agent: MarketToolAgent | None = None) -> None:
        self.rag_index = rag_index or default_rag_index
        self.tool_agent = tool_agent or MarketToolAgent()

    async def run(self, state: MarketIntelligenceState) -> dict:
        ticker = state.get("ticker", state["symbol"]).upper()
        market = state.get("market", "NSE")
        tool_result = await self.tool_agent.run(ticker, market)
        market_data = tool_result.get("get_price", {"symbol": ticker, "market": market.upper(), "price": None, "closes": [], "source": "unavailable"})
        news = tool_result.get("get_news", []) if state.get("include_news", True) else []
        errors: list[str] = tool_result.get("errors", [])
        closes = market_data.get("closes", [])
        return {
            "ticker": ticker,
            "market_data": market_data,
            "news": news,
            "headlines": news,
            "technicals": tool_result.get("get_technicals") or compute_technicals(closes),
            "rag_context": self.rag_index.query(ticker, f"{ticker} risks earnings guidance debt outlook"),
            "tool_calls": tool_result["tool_calls"],
            "errors": errors,
            "research_findings": f"Collected {len(news)} headlines and {len(closes)} daily prices for {ticker} on {market.upper()}.",
        }
