"""Resilient HTTP primitives shared by market-data providers."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from market_intelligence.config.settings import Settings, get_settings
from market_intelligence.tools.ratelimit import AsyncRateLimiter


class ProviderError(RuntimeError):
    """A provider failed after safe retries."""


class JsonProvider:
    def __init__(
        self,
        name: str,
        limiter: AsyncRateLimiter,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = name
        self.settings = settings or get_settings()
        self.limiter = limiter
        self.client = client

    async def get_json(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        attempts = self.settings.provider_max_retries + 1
        last_error: Exception | None = None
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.settings.request_timeout_seconds)
        try:
            for attempt in range(attempts):
                await self.limiter.acquire()
                try:
                    response = await client.get(url, params=params)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        raise httpx.HTTPStatusError(
                            f"retryable status {response.status_code}", request=response.request, response=response
                        )
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ProviderError(f"{self.name} returned an unexpected payload")
                    return payload
                except (httpx.HTTPError, ValueError, ProviderError) as exc:
                    last_error = exc
                    if attempt + 1 < attempts:
                        await asyncio.sleep(self.settings.provider_backoff_seconds * (2**attempt))
            raise ProviderError(f"{self.name} request failed: {last_error}") from last_error
        finally:
            if owns_client:
                await client.aclose()
