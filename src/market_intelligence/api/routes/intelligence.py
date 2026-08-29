from fastapi import APIRouter, HTTPException, status

from market_intelligence.api.schemas.requests import IntelligenceRequest
from market_intelligence.api.schemas.responses import IntelligenceResponse
from market_intelligence.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/intelligence", tags=["intelligence"])
service = IntelligenceService()


@router.post(
    "/analyze",
    response_model=IntelligenceResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze(request: IntelligenceRequest) -> IntelligenceResponse:
    try:
        return await service.analyze(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market intelligence analysis failed",
        ) from exc
