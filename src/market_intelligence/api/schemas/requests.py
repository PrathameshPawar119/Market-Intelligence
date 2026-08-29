from typing import Literal

from pydantic import BaseModel, Field


class IntelligenceRequest(BaseModel):
    """Input accepted by the market intelligence endpoint."""

    symbol: str = Field(min_length=1, max_length=20)
    market: str = Field(min_length=1, max_length=20)
    analysis_type: Literal["fundamental", "technical", "sentiment"] = "fundamental"
    include_news: bool = True
