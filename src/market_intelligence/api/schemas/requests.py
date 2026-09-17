from typing import Literal

from pydantic import BaseModel, Field


class IntelligenceRequest(BaseModel):
    """Input accepted by the market intelligence endpoint."""

    symbol: str = Field(min_length=1, max_length=20)
    market: str = Field(min_length=1, max_length=20)
    analysis_type: Literal["fundamental", "technical", "sentiment"] = "fundamental"
    include_news: bool = True


class SignalRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    market: str = Field(default="NSE", min_length=1, max_length=20)
    include_news: bool = True

    def as_intelligence_request(self) -> IntelligenceRequest:
        return IntelligenceRequest(symbol=self.ticker, market=self.market, analysis_type="sentiment", include_news=self.include_news)


class DocumentRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    source: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=20)
