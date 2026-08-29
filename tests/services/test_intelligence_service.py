import pytest

from market_intelligence.api.schemas.requests import IntelligenceRequest
from market_intelligence.services.intelligence_service import IntelligenceService


@pytest.mark.asyncio
async def test_service_returns_analysis() -> None:
    result = await IntelligenceService().analyze(
        IntelligenceRequest(symbol="TCS", market="NSE")
    )

    assert result.symbol == "TCS"
    assert result.report
