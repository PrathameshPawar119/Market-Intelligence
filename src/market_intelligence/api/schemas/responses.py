from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class IntelligenceResponse(BaseModel):
    symbol: str
    market: str
    analysis_type: str
    include_news: bool
    market_data: dict[str, Any]
    news: list[dict[str, Any]]
    research_findings: str
    analysis: str
    report: str
    ticker: str | None = None
    headlines: list[dict[str, Any]] = []
    sentiment: dict[str, Any] = {}
    signal: dict[str, Any] = {}
    technicals: dict[str, Any] = {}
    tool_calls: list[str] = []
    errors: list[str] = []


class BatchSignalResult(BaseModel):
    ticker: str
    result: IntelligenceResponse | None = None
    error: str | None = None
