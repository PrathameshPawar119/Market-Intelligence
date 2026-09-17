from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from market_intelligence.api.rate_limit import enforce_rate_limit
from market_intelligence.api.schemas.requests import DocumentRequest, SignalRequest
from market_intelligence.api.schemas.responses import (
    BatchSignalResult,
    IntelligenceResponse,
)
from market_intelligence.observability import ledger
from market_intelligence.rag import default_rag_index
from market_intelligence.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/signals", tags=["signals"])
service = IntelligenceService()


class BatchSignalRequest(BaseModel):
    tickers: list[SignalRequest]


@router.post("/analyze", response_model=IntelligenceResponse)
async def analyze_signal(request: SignalRequest, _: None = Depends(enforce_rate_limit)) -> IntelligenceResponse:
    try:
        return await service.analyze(request.as_intelligence_request())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Signal generation failed") from exc


@router.post("/batch", response_model=list[BatchSignalResult])
async def analyze_batch(request: BatchSignalRequest, _: None = Depends(enforce_rate_limit)) -> list[BatchSignalResult]:
    if not request.tickers or len(request.tickers) > 5:
        raise HTTPException(status_code=422, detail="Provide between 1 and 5 tickers")
    outcomes = await service.analyze_many([item.as_intelligence_request() for item in request.tickers])
    return [
        BatchSignalResult(ticker=item.ticker.upper(), result=outcome)
        if isinstance(outcome, IntelligenceResponse)
        else BatchSignalResult(ticker=item.ticker.upper(), error=str(outcome))
        for item, outcome in zip(request.tickers, outcomes, strict=True)
    ]


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def ingest_document(request: DocumentRequest) -> dict[str, int]:
    return {"chunks_indexed": default_rag_index.ingest(request.ticker, request.source, request.text)}


@router.get("/{ticker}/knowledge")
async def query_knowledge(ticker: str, question: str) -> dict[str, object]:
    return {"ticker": ticker.upper(), "chunks": default_rag_index.query(ticker, question)}


@router.get("/usage/daily")
async def daily_usage() -> dict[str, object]:
    return ledger.dashboard()
