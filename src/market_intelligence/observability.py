"""Structured tracing and token/cost accounting with no hosted dependency."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass

from market_intelligence.config.settings import get_settings

logger = logging.getLogger("market_intelligence.trace")


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        settings = get_settings()
        return (self.input_tokens * settings.input_token_cost_per_million_usd + self.output_tokens * settings.output_token_cost_per_million_usd) / 1_000_000


class UsageLedger:
    def __init__(self) -> None:
        self.by_user: dict[str, Usage] = defaultdict(Usage)
        self.by_ticker: dict[str, Usage] = defaultdict(Usage)

    def record(self, user_id: str, ticker: str, input_tokens: int, output_tokens: int) -> Usage:
        for bucket in (self.by_user[user_id], self.by_ticker[ticker.upper()]):
            bucket.input_tokens += input_tokens
            bucket.output_tokens += output_tokens
        usage = self.by_user[user_id]
        if usage.estimated_cost_usd > get_settings().daily_cost_alert_usd:
            logger.warning("daily_cost_alert userId=%s estimatedCostUsd=%.4f", user_id, usage.estimated_cost_usd)
        return usage

    def dashboard(self) -> dict[str, object]:
        return {
            "total": {"input_tokens": sum(item.input_tokens for item in self.by_user.values()), "output_tokens": sum(item.output_tokens for item in self.by_user.values()), "estimated_cost_usd": round(sum(item.estimated_cost_usd for item in self.by_user.values()), 6)},
            "by_user": {key: {"input_tokens": value.input_tokens, "output_tokens": value.output_tokens, "estimated_cost_usd": round(value.estimated_cost_usd, 6)} for key, value in self.by_user.items()},
            "by_ticker": {key: {"input_tokens": value.input_tokens, "output_tokens": value.output_tokens, "estimated_cost_usd": round(value.estimated_cost_usd, 6)} for key, value in self.by_ticker.items()},
        }


ledger = UsageLedger()


class Trace:
    def __init__(self, ticker: str, user_id: str = "anonymous") -> None:
        self.trace_id = str(uuid.uuid4())
        self.ticker = ticker.upper()
        self.user_id = user_id
        self.started = time.perf_counter()

    def finish(self, *, input_tokens: int = 0, output_tokens: int = 0, success: bool = True) -> None:
        ledger.record(self.user_id, self.ticker, input_tokens, output_tokens)
        logger.info("analysis_complete traceId=%s ticker=%s tokensUsed=%s latencyMs=%s success=%s", self.trace_id, self.ticker, input_tokens + output_tokens, round((time.perf_counter() - self.started) * 1000), success)


async def invoke_llm(llm: object, prompt: str, ticker: str) -> object:
    """Invoke an LLM and emit a Langfuse/LangSmith-compatible trace record.

    A hosted tracer can consume these structured fields; keeping the wrapper
    local avoids dropping signal generation when optional tracing is down.
    """
    started = time.perf_counter()
    response = await llm.ainvoke(prompt)  # type: ignore[attr-defined]
    metadata = getattr(response, "usage_metadata", {}) or {}
    input_tokens = int(metadata.get("input_tokens", 0))
    output_tokens = int(metadata.get("output_tokens", 0))
    ledger.record("anonymous", ticker, input_tokens, output_tokens)
    logger.info("llm_call ticker=%s prompt=%r response=%r inputTokens=%s outputTokens=%s latencyMs=%s success=true", ticker.upper(), prompt, str(getattr(response, "content", response)), input_tokens, output_tokens, round((time.perf_counter() - started) * 1000))
    return response
