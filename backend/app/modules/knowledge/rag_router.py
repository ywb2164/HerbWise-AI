from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.knowledge.normalizer import MedicineNameNormalizer
from app.modules.knowledge.models import MedicineItem
from app.modules.knowledge.rag_models import RAGEvidenceRecord, RAGRetrievalRecord
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


def _retrieval_data(
    item: RAGRetrievalRecord, evidence: list[RAGEvidenceRecord]
) -> dict:
    return {
        "retrieval_id": item.retrieval_id,
        "task_id": item.task_id,
        "learner_id": item.learner_id,
        "query": item.query,
        "provider": item.provider,
        "dataset_id": item.dataset_id,
        "medicine_id": item.medicine_id,
        "returned_count": item.returned_count,
        "latency_ms": item.latency_ms,
        "cache_hit": item.cache_hit,
        "replay_used": item.replay_used,
        "fallback_used": item.fallback_used,
        "status": item.status,
        "error_code": item.error_code,
        "metadata": item.metadata_json or {},
        "evidences": [
            {
                "evidence_id": row.evidence_id,
                "document_id": row.document_id,
                "document_name": row.document_name,
                "chunk_id": row.chunk_id,
                "page_number": row.page_number,
                "content": row.content_snapshot,
                "score": row.score,
                "citation": row.citation,
                "rank": row.rank,
                "retained_reason": row.retained_reason,
                "duplicate_of": row.duplicate_of,
            }
            for row in evidence
        ],
        "created_at": item.created_at,
    }


@router.get(
    "/retrievals/{retrieval_id}",
    response_model=ApiResponse,
    summary="Get retrieval record",
    description="Return one retrieval with retained evidence and learner isolation.",
)
async def get_retrieval(
    retrieval_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await session.scalar(
        select(RAGRetrievalRecord).where(
            RAGRetrievalRecord.retrieval_id == retrieval_id
        )
    )
    if item is None:
        raise __import__(
            "app.core.exceptions", fromlist=["NotFoundException"]
        ).NotFoundException("Retrieval not found")
    if item.learner_id:
        ensure_learner_access(user, item.learner_id)
    evidence = list(
        (
            await session.scalars(
                select(RAGEvidenceRecord).where(
                    RAGEvidenceRecord.retrieval_id == retrieval_id
                )
            )
        ).all()
    )
    return success(_retrieval_data(item, evidence))


@router.get(
    "/retrievals",
    response_model=ApiResponse,
    summary="List retrieval records",
    description="List retrieval records subject to learner data isolation.",
)
async def list_retrievals(
    learner_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if learner_id:
        ensure_learner_access(user, learner_id)
    elif "student" in {role.code for role in user.roles} and not user.is_superuser:
        learner_id = user.learner_id
    stmt = select(RAGRetrievalRecord)
    if learner_id:
        stmt = stmt.where(RAGRetrievalRecord.learner_id == learner_id)
    items = list(
        (
            await session.scalars(
                stmt.order_by(RAGRetrievalRecord.id.desc()).limit(100)
            )
        ).all()
    )
    return success({"items": [_retrieval_data(item, []) for item in items]})
