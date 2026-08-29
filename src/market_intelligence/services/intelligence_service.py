from market_intelligence.api.schemas.requests import IntelligenceRequest
from market_intelligence.api.schemas.responses import IntelligenceResponse
from market_intelligence.graph.graph import build_graph


class IntelligenceService:
    """Application service that coordinates market intelligence requests."""

    def __init__(self) -> None:
        self._graph = build_graph()

    async def analyze(self, request: IntelligenceRequest) -> IntelligenceResponse:
        result = await self._graph.ainvoke(request.model_dump())
        return IntelligenceResponse.model_validate(result)
