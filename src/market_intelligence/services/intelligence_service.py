from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from market_intelligence.api.schemas.requests import IntelligenceRequest
from market_intelligence.api.schemas.responses import IntelligenceResponse
from market_intelligence.config.settings import get_settings
from market_intelligence.graph.graph import build_graph
from market_intelligence.observability import Trace


@dataclass
class _CacheEntry:
    response: IntelligenceResponse
    expires_at: float


class IntelligenceService:
    """Application service that coordinates market intelligence requests."""

    def __init__(self) -> None:
        self._graph = build_graph()
        self._cache: dict[tuple[str, str, str, bool], _CacheEntry] = {}
        self._cache_lock = asyncio.Lock()

    async def analyze(self, request: IntelligenceRequest) -> IntelligenceResponse:
        key = (request.symbol.upper(), request.market.upper(), request.analysis_type, request.include_news)
        now = time.monotonic()
        async with self._cache_lock:
            cached = self._cache.get(key)
            if cached and cached.expires_at > now:
                return cached.response.model_copy(deep=True)
        trace = Trace(request.symbol)
        try:
            payload = request.model_dump() | {"ticker": request.symbol.upper()}
            result = await self._graph.ainvoke(payload)
            response = IntelligenceResponse.model_validate(result)
            trace.finish(input_tokens=0, output_tokens=len(response.analysis.split()))
            async with self._cache_lock:
                self._cache[key] = _CacheEntry(response=response, expires_at=now + get_settings().cache_ttl_seconds)
            return response
        except Exception:
            trace.finish(success=False)
            raise

    async def analyze_many(self, requests: list[IntelligenceRequest]) -> list[IntelligenceResponse | Exception]:
        """Analyze independent tickers concurrently; one provider failure is isolated."""
        limit = asyncio.Semaphore(get_settings().max_parallel_tickers)

        async def bounded(request: IntelligenceRequest) -> IntelligenceResponse:
            async with limit:
                return await self.analyze(request)

        return await asyncio.gather(*(bounded(request) for request in requests), return_exceptions=True)
