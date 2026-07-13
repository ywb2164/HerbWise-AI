from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.integrations.runtime_model import runtime_model_registry
from app.integrations.secrets import SecretResolver
from app.integrations.vision.local import UltralyticsLocalVisionProvider
from app.modules.auth.models import User
from app.modules.auth.service import get_current_user

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get(
    "",
    summary="Get configured AI capabilities",
    description="Expose safe mode and availability flags without secrets, provider URLs, or local model paths.",
)
async def capabilities(user: User = Depends(get_current_user)) -> dict[str, object]:
    settings = get_settings()
    local = UltralyticsLocalVisionProvider.status()
    secret = SecretResolver.is_configured("env:MODEL_API_KEY")
    runtime_model = runtime_model_registry.get_for_user(user.id)
    runtime_configured = runtime_model is not None
    return {
        "ai_mode": settings.ai_mode,
        "vision_mode": settings.effective_vision_mode(),
        "llm_mode": settings.llm_mode,
        "rag_mode": settings.rag_mode,
        "qwen_configured": bool(
            runtime_configured
            or settings.model_api_base_url
            and settings.qwen_vl_model
            and secret
        ),
        "local_model_configured": local["configured"],
        "local_model_loaded": local["loaded"],
        "generation_model_configured": bool(
            runtime_configured or settings.generation_model and secret
        ),
        "review_model_configured": bool(
            runtime_configured or settings.review_model and secret
        ),
        "mock_fallback_available": True,
    }
