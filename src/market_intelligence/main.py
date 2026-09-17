import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from market_intelligence.api.routes.health import router as health_router
from market_intelligence.api.routes.intelligence import router as intelligence_router
from market_intelligence.api.routes.signals import router as signals_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Market Intelligence AI Service", version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
