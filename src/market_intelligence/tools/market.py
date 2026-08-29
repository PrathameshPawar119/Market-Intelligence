from typing import Any


async def get_market_data(symbol: str, market: str) -> dict[str, Any]:
    """Return market data in a stable shape for a future provider integration."""

    # TODO: Replace mock data with a financial data provider.
    return {
        "symbol": symbol.upper(),
        "market": market.upper(),
        "price": None,
        "currency": "INR" if market.upper() == "NSE" else None,
        "source": "mock",
    }
