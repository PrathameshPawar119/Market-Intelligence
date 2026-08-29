from typing import Any, TypedDict


class MarketIntelligenceState(TypedDict, total=False):
    symbol: str
    market: str
    analysis_type: str
    include_news: bool
    market_data: dict[str, Any]
    news: list[dict[str, Any]]
    research_findings: str
    analysis: str
    report: str
