import pytest

from market_intelligence.agents.analysis_agent import AnalysisAgent
from market_intelligence.agents.report_agent import ReportAgent
from market_intelligence.agents.research_agent import ResearchAgent
from market_intelligence.rag import LocalRagIndex


class FakeToolAgent:
    async def run(self, ticker: str, market: str) -> dict:
        return {
            "tool_calls": ["get_news", "get_price", "get_technicals"],
            "get_news": [{"headline": "INFY reports record profit growth"}],
            "get_price": {"closes": [100.0] * 25 + [110.0], "source": "test"},
            "get_technicals": {"trend": "bullish", "rsi_14": 60},
        }


@pytest.mark.asyncio
async def test_fetch_news_analyse_sentiment_generate_signal_nodes() -> None:
    index = LocalRagIndex()
    index.ingest("INFY", "Q1 earnings call", "Management identified currency volatility and client spending risks.")
    fetched = await ResearchAgent(index, FakeToolAgent()).run({"symbol": "INFY", "market": "NSE"})
    analysed = await AnalysisAgent().run(fetched)
    result = await ReportAgent().run(fetched | analysed)

    assert fetched["tool_calls"] == ["get_news", "get_price", "get_technicals"]
    assert analysed["sentiment"]["label"] == "positive"
    assert result["signal"]["action"] == "BUY"
    assert "currency volatility" in result["signal"]["risks"][0]
