from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from market_intelligence.agents.analysis_agent import AnalysisAgent
from market_intelligence.agents.report_agent import ReportAgent
from market_intelligence.agents.research_agent import ResearchAgent
from market_intelligence.graph.nodes.analysis import analysis_node
from market_intelligence.graph.nodes.report import report_node
from market_intelligence.graph.nodes.research import research_node
from market_intelligence.graph.state import MarketIntelligenceState


def build_graph(
    research_agent: ResearchAgent | None = None,
    analysis_agent: AnalysisAgent | None = None,
    report_agent: ReportAgent | None = None,
):
    """Build FetchNews → AnalyseSentiment → GenerateSignal.

    Dependency injection keeps each node independently testable without
    touching an external market provider or an LLM.
    """

    workflow = StateGraph(MarketIntelligenceState)
    workflow.add_node("fetch_news", research_node(research_agent or ResearchAgent()))
    workflow.add_node("analyse_sentiment", analysis_node(analysis_agent or AnalysisAgent()))
    workflow.add_node("generate_signal", report_node(report_agent or ReportAgent()))
    workflow.add_edge(START, "fetch_news")
    workflow.add_edge("fetch_news", "analyse_sentiment")
    workflow.add_edge("analyse_sentiment", "generate_signal")
    workflow.add_edge("generate_signal", END)
    return workflow.compile()
