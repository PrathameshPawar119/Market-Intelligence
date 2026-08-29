import pytest

from market_intelligence.graph.graph import build_graph


class FakeResearchAgent:
    async def run(self, state: dict) -> dict:
        return {
            "market_data": {"source": "test"},
            "news": [],
            "research_findings": "test findings",
        }


class FakeAnalysisAgent:
    async def run(self, state: dict) -> dict:
        assert state["research_findings"] == "test findings"
        return {"analysis": "test analysis"}


class FakeReportAgent:
    async def run(self, state: dict) -> dict:
        assert state["analysis"] == "test analysis"
        return {"report": "test report"}


@pytest.mark.asyncio
async def test_graph_runs_research_analysis_report_in_order() -> None:
    graph = build_graph(FakeResearchAgent(), FakeAnalysisAgent(), FakeReportAgent())

    result = await graph.ainvoke(
        {
            "symbol": "RELIANCE",
            "market": "NSE",
            "analysis_type": "fundamental",
            "include_news": False,
        }
    )

    assert result["report"] == "test report"
