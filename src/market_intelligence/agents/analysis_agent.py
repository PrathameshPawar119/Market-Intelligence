"""Second graph node: explainable headline sentiment analysis."""

from __future__ import annotations

from typing import Any

from market_intelligence.config.settings import get_settings
from market_intelligence.graph.state import MarketIntelligenceState
from market_intelligence.llm.models import get_chat_model
from market_intelligence.observability import invoke_llm

POSITIVE = {"beat", "growth", "profit", "upgrade", "win", "record", "bullish", "buyback", "dividend", "approval", "surge"}
NEGATIVE = {"risk", "fall", "loss", "downgrade", "fraud", "probe", "miss", "cut", "layoff", "lawsuit", "bearish", "decline"}


class AnalysisAgent:
    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def run(self, state: MarketIntelligenceState) -> dict[str, Any]:
        headlines = state.get("headlines", state.get("news", []))
        text = " ".join(f"{item.get('headline', '')} {item.get('summary', '')}".lower() for item in headlines)
        positive = sum(text.count(word) for word in POSITIVE)
        negative = sum(text.count(word) for word in NEGATIVE)
        score = 0.0 if positive + negative == 0 else round((positive - negative) / (positive + negative), 3)
        label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
        sentiment = {"label": label, "score": score, "headline_count": len(headlines), "positive_terms": positive, "negative_terms": negative}
        analysis = f"News sentiment is {label} ({score:+.3f}) across {len(headlines)} headlines."
        # An LLM is used to add a concise investment-risk explanation only
        # when one is configured; deterministic sentiment remains available in
        # offline/CI environments.
        settings = get_settings()
        if self._llm is not None or (settings.enable_llm and settings.has_configured_provider):
            llm = self._llm or get_chat_model()
            prompt = ("Summarise market-moving risks in <=80 words. Do not give financial advice. "
                      f"Ticker: {state.get('ticker', state.get('symbol'))}; headlines: {headlines[:5]}; "
                      f"filing context: {state.get('rag_context', [])[:2]}")
            try:
                response = await invoke_llm(llm, prompt, str(state.get("ticker", state.get("symbol", ""))))
                analysis = str(response.content)
            except Exception:  # noqa: BLE001 - provider exceptions vary by SDK
                analysis += " LLM narrative is temporarily unavailable."
        return {"sentiment": sentiment, "analysis": analysis}
