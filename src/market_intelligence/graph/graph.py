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
    """Build the linear workflow, keeping agent dependencies injectable for tests."""

    workflow = StateGraph(MarketIntelligenceState)
    workflow.add_node("research", research_node(research_agent or ResearchAgent()))
    workflow.add_node("analysis", analysis_node(analysis_agent or AnalysisAgent()))
    workflow.add_node("report", report_node(report_agent or ReportAgent()))
    workflow.add_edge(START, "research")
    workflow.add_edge("research", "analysis")
    workflow.add_edge("analysis", "report")
    workflow.add_edge("report", END)
    return workflow.compile()
