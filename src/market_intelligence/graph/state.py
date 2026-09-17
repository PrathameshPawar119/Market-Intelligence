from typing import Any, TypedDict


class MarketIntelligenceState(TypedDict, total=False):
    # ``symbol`` is retained for the existing HTTP contract.  New code uses
    # ticker; both are populated at the graph boundary.
    ticker: str
    symbol: str
    market: str
    analysis_type: str
    include_news: bool
    market_data: dict[str, Any]
    news: list[dict[str, Any]]
    headlines: list[dict[str, Any]]
    sentiment: dict[str, Any]
    signal: dict[str, Any]
    technicals: dict[str, Any]
    rag_context: list[dict[str, Any]]
    tool_calls: list[str]
    errors: list[str]
    research_findings: str
    analysis: str
    report: str
