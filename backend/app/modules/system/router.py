from fastapi import APIRouter

from app.common.datetime import now_api_datetime
from app.core.database import check_database
from app.core.exceptions import ExternalServiceException
from app.core.redis import check_redis

router = APIRouter(tags=["system"])


@router.get(
    "/", summary="API root", description="Return the HerbWise API service identity."
)
async def root() -> dict[str, str]:
    return {"name": "HerbWise AI API", "status": "online"}


@router.get(
    "/health",
    summary="Health check",
    description="Return process liveness without checking dependencies.",
)
async def health() -> dict[str, str]:
    return {"status": "alive", "timestamp": now_api_datetime()}


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check database and Redis readiness.",
)
async def ready() -> dict[str, str]:
    try:
        await check_database()
    except Exception as exc:
        raise ExternalServiceException("Database dependency is unavailable") from exc
    try:
        await check_redis()
    except Exception as exc:
        raise ExternalServiceException("Redis dependency is unavailable") from exc
    return {"status": "ready", "database": "connected", "redis": "connected"}
