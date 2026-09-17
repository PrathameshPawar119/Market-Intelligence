"""Small async rate limiter used before making third-party calls."""

from __future__ import annotations

import asyncio
import time
from collections import deque


class AsyncRateLimiter:
    """A process-local sliding-window limiter.

    Provider limits are account-wide in production, so deployments with more
    than one worker should replace this with the Redis implementation at the
    gateway.  Keeping the limiter here protects local runs and tests too.
    """

    def __init__(self, max_calls: int, period_seconds: float = 60.0) -> None:
        self.max_calls = max(1, max_calls)
        self.period_seconds = period_seconds
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= self.period_seconds:
                    self._calls.popleft()
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return
                delay = self.period_seconds - (now - self._calls[0])
            await asyncio.sleep(max(delay, 0.001))
