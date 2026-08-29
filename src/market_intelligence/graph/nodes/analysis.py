from market_intelligence.agents.analysis_agent import AnalysisAgent
from market_intelligence.graph.state import MarketIntelligenceState


def analysis_node(agent: AnalysisAgent):
    async def run(state: MarketIntelligenceState) -> dict[str, str]:
        return await agent.run(state)

    return run
