from market_intelligence.rag import LocalRagIndex


def test_rag_returns_earnings_risk_chunk() -> None:
    index = LocalRagIndex()
    index.ingest("INFY", "FY26 earnings call", "Key risks include weak discretionary demand, currency volatility and delayed client decisions.")
    index.ingest("TCS", "FY26 earnings call", "Risks relate to hiring and attrition.")

    results = index.query("INFY", "What risks were mentioned in the last earnings call?")

    assert len(results) == 1
    assert "currency volatility" in results[0]["text"]
