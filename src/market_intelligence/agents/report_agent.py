"""Final graph node: combine news, technicals and retrieved risks into a signal."""

from __future__ import annotations

from typing import Any

from market_intelligence.graph.state import MarketIntelligenceState


class ReportAgent:
    async def run(self, state: MarketIntelligenceState) -> dict[str, Any]:
        sentiment = state.get("sentiment", {})
        technicals = state.get("technicals", {})
        sentiment_score = float(sentiment.get("score", 0))
        trend = technicals.get("trend", "unknown")
        score = sentiment_score + (0.35 if trend == "bullish" else -0.35 if trend == "bearish" else 0)
        action = "BUY" if score >= 0.35 else "SELL" if score <= -0.35 else "HOLD"
        confidence = min(0.95, round(0.45 + min(abs(score), 0.5), 2))
        risks = [item["text"][:240] for item in state.get("rag_context", [])[:2]]
        signal = {
            "action": action,
            "confidence": confidence,
            "score": round(score, 3),
            "reason": f"Sentiment is {sentiment.get('label', 'neutral')} and technical trend is {trend}.",
            "risks": risks,
            "disclaimer": "Informational signal only; not investment advice.",
        }
        ticker = state.get("ticker", state.get("symbol", "")).upper()
        report = f"{ticker} signal: {action} (confidence {confidence:.0%}). {signal['reason']} {state.get('analysis', '')}"
        return {"signal": signal, "report": report}
