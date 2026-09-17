import asyncio
import time

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


@pytest.mark.asyncio
async def test_service_analyzes_five_tickers_concurrently(monkeypatch) -> None:
    service = IntelligenceService()

    async def fake_analyze(request: IntelligenceRequest):
        await asyncio.sleep(0.03)
        if request.symbol == "BAD":
            raise RuntimeError("provider unavailable")
        return request.symbol

    monkeypatch.setattr(service, "analyze", fake_analyze)
    started = time.perf_counter()
    results = await service.analyze_many([IntelligenceRequest(symbol=symbol, market="NSE") for symbol in ["INFY", "TCS", "HDFCBANK", "RELIANCE", "BAD"]])

    assert time.perf_counter() - started < 0.15
    assert results[:4] == ["INFY", "TCS", "HDFCBANK", "RELIANCE"]
    assert isinstance(results[4], RuntimeError)
