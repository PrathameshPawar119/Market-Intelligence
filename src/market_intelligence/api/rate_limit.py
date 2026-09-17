"""Per-user request limiting with Redis when configured, memory otherwise."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from market_intelligence.config.settings import get_settings

logger = logging.getLogger(__name__)


class RequestRateLimiter:
    def __init__(self) -> None:
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._redis = None

    async def _redis_client(self):
        settings = get_settings()
        if not settings.redis_url:
            return None
        if self._redis is None:
            try:
                from redis.asyncio import Redis

                self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
            except ImportError:
                return None
        return self._redis

    async def check(self, user_id: str) -> None:
        settings = get_settings()
        redis = await self._redis_client()
        if redis is not None:
            try:
                key = f"market-intelligence:rate:{user_id}:{int(time.time() // 60)}"
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, 60)
                if count > settings.requests_per_minute_per_user:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded; retry in one minute")
                return
            except HTTPException:
                raise
            except Exception as exc:  # noqa: BLE001 - Redis outage falls back safely
                logger.warning("Redis rate limiter unavailable; using local fallback: %s", exc)
        now = time.monotonic()
        calls = self._calls[user_id]
        while calls and now - calls[0] >= 60:
            calls.popleft()
        if len(calls) >= settings.requests_per_minute_per_user:
            raise HTTPException(status_code=429, detail="Rate limit exceeded; retry in one minute")
        calls.append(now)


rate_limiter = RequestRateLimiter()


async def enforce_rate_limit(request: Request) -> None:
    # Spring/JWT can forward its authenticated subject in this header.  The
    # fallback makes the Python service safe when run directly in development.
    await rate_limiter.check(request.headers.get("X-User-Id", request.client.host if request.client else "anonymous"))
