from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.knowledge.normalizer import MedicineNameNormalizer
from app.modules.knowledge.models import MedicineItem
from app.modules.knowledge.rag_service import (
    HybridKnowledgeService,
    KnowledgeQueryBuilder,
)
from app.integrations.contracts import RAGQuery

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge-retrieval"],
    dependencies=[Depends(get_current_user)],
)


class RetrievePayload(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    medicine_name: str | None = Field(default=None, max_length=128)
    task_type: str = Field(default="identification", max_length=64)
    query: str | None = Field(default=None, max_length=500)
    top_k: int = Field(default=8, ge=1, le=20)


@router.post(
    "/retrieve",
    response_model=ApiResponse,
    summary="Retrieve knowledge evidence",
    description="Retrieve structured and configured RAG evidence without accepting provider credentials or dataset overrides.",
)
async def retrieve(
    payload: RetrievePayload,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, payload.learner_id)
    normalized = await MedicineNameNormalizer().normalize(
        session, payload.medicine_name or ""
    )
    medicine = (
        await session.get(MedicineItem, normalized.medicine_id)
        if normalized.matched
        else None
    )
    query = KnowledgeQueryBuilder().build(medicine, payload.task_type, payload.query)
    retrieval_id, result = await HybridKnowledgeService().retrieve(
        session,
        RAGQuery(
            query=query,
            learner_id=payload.learner_id,
            medicine_id=normalized.medicine_id,
            medicine_name=normalized.standard_name_zh,
            task_type=payload.task_type,
            top_k=payload.top_k,
        ),
    )
    return success({"retrieval_id": retrieval_id, **result.model_dump(mode="json")})
