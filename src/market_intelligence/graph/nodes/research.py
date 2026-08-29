from market_intelligence.agents.research_agent import ResearchAgent
from market_intelligence.graph.state import MarketIntelligenceState


def research_node(agent: ResearchAgent):
    async def run(state: MarketIntelligenceState) -> dict:
        return await agent.run(state)

    return run
