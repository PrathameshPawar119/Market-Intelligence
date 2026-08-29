from market_intelligence.graph.state import MarketIntelligenceState
from market_intelligence.tools.market import get_market_data
from market_intelligence.tools.news import get_news


class ResearchAgent:
    async def run(self, state: MarketIntelligenceState) -> dict:
        symbol = state["symbol"]
        market = state["market"]
        market_data = await get_market_data(symbol, market)
        news = await get_news(symbol, market) if state.get("include_news", True) else []
        return {
            "market_data": market_data,
            "news": news,
            "research_findings": (
                f"Research collected for {symbol.upper()} on {market.upper()} "
                f"using {market_data['source']} data."
            ),
        }
