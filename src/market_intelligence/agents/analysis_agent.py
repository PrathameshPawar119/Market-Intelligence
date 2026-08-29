from __future__ import annotations

from typing import Any

from market_intelligence.config.settings import get_settings
from market_intelligence.graph.state import MarketIntelligenceState
from market_intelligence.llm.models import get_chat_model


class AnalysisAgent:
    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def run(self, state: MarketIntelligenceState) -> dict[str, str]:
        prompt = (
            f"Analyze {state['symbol']} on {state['market']} using "
            f"a {state['analysis_type']} approach.\n"
            f"Research: {state.get('research_findings', '')}\n"
            f"Market data: {state.get('market_data', {})}\n"
            f"News: {state.get('news', [])}"
        )
        settings = get_settings()
        if self._llm is None and not settings.has_configured_provider:
            # TODO: Require a configured LLM in production deployments.
            return {"analysis": f"Mock {state['analysis_type']} analysis for {state['symbol']}."}

        llm = self._llm or get_chat_model()
        response = await llm.ainvoke(prompt)
        return {"analysis": str(response.content)}
