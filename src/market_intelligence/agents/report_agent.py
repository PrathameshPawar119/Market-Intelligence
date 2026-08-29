from market_intelligence.graph.state import MarketIntelligenceState


class ReportAgent:
    async def run(self, state: MarketIntelligenceState) -> dict[str, str]:
        return {
            "report": (
                f"{state['symbol'].upper()} ({state['market'].upper()}) report\n\n"
                f"Analysis type: {state['analysis_type']}\n"
                f"{state.get('analysis', '')}"
            )
        }
