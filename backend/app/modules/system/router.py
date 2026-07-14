from fastapi import APIRouter

from app.common.datetime import now_api_datetime
from app.core.config import get_settings
from app.core.database import check_database
from app.core.exceptions import ExternalServiceException
from app.core.redis import check_redis
from app.integrations.secrets import SecretResolver
from app.integrations.vision.local import UltralyticsLocalVisionProvider

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
    settings = get_settings()
    if settings.llm_mode == "real":
        if not (
            settings.model_api_base_url
            and SecretResolver.is_configured("env:MODEL_API_KEY")
            and settings.generation_model
            and settings.review_model
        ):
            raise ExternalServiceException("Real LLM configuration is unavailable")
    mode = settings.effective_vision_mode()
    qwen_ready = bool(
        settings.model_api_base_url
        and settings.qwen_vl_model
        and SecretResolver.is_configured("env:MODEL_API_KEY")
    )
    local_ready = bool(UltralyticsLocalVisionProvider.status()["configured"])
    if mode != "mock" and not qwen_ready:
        raise ExternalServiceException("Qwen-VL primary recognition configuration is unavailable")
    status = "degraded" if mode != "mock" and not local_ready else "ready"
    return {"status": status, "database": "connected", "redis": "connected"}
