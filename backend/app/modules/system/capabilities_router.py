from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.integrations.runtime_model import runtime_model_registry
from app.integrations.secrets import SecretResolver
from app.integrations.vision.local import UltralyticsLocalVisionProvider
from app.modules.knowledge.catalog import KnowledgeCatalog
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
    knowledge = KnowledgeCatalog.status()
    secret = SecretResolver.is_configured("env:MODEL_API_KEY")
    runtime_vision = runtime_model_registry.get_for_user(user.id, "vision")
    runtime_text = runtime_model_registry.get_for_user(user.id, "text")
    return {
        "ai_mode": settings.ai_mode,
        "vision_mode": "mock"
        if settings.effective_vision_mode() == "mock"
        else "fixed_pipeline",
        "llm_mode": settings.llm_mode,
        "rag_mode": settings.rag_mode,
        "qwen_configured": bool(
            runtime_vision is not None
            or settings.model_api_base_url
            and settings.qwen_vl_model
            and secret
        ),
        "local_model_configured": local["configured"],
        "local_model_loaded": local["loaded"],
        "knowledge_catalog_loaded": knowledge["loaded"],
        "knowledge_catalog_record_count": knowledge["record_count"],
        "generation_model_configured": bool(
            runtime_text is not None or settings.generation_model and secret
        ),
        "review_model_configured": bool(
            runtime_text is not None or settings.review_model and secret
        ),
        "mock_fallback_available": True,
    }
