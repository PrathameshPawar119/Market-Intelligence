from market_intelligence.agents.report_agent import ReportAgent
from market_intelligence.graph.state import MarketIntelligenceState


def report_node(agent: ReportAgent):
    async def run(state: MarketIntelligenceState) -> dict[str, str]:
        return await agent.run(state)

    return run
