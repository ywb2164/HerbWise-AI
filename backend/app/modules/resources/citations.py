from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.rag_models import RAGEvidenceRecord, RAGRetrievalRecord


class CitationValidationError(AppException):
    status_code = 422
    code = 1422


async def resolve_citations(
    session: AsyncSession, retrieval_id: str, evidence_ids: list[str]
) -> list[dict]:
    if not evidence_ids:
        return []
    retrieval = await session.scalar(
        select(RAGRetrievalRecord).where(
            RAGRetrievalRecord.retrieval_id == retrieval_id
        )
    )
    if retrieval is None:
        raise CitationValidationError("Retrieval does not exist")
    rows = list(
        (
            await session.scalars(
                select(RAGEvidenceRecord).where(
                    RAGEvidenceRecord.retrieval_id == retrieval_id,
                    RAGEvidenceRecord.evidence_id.in_(set(evidence_ids)),
                )
            )
        ).all()
    )
    if len({item.evidence_id for item in rows}) != len(set(evidence_ids)):
        raise CitationValidationError(
            "One or more evidence IDs are invalid for this retrieval"
        )
    return [
        {
            "evidence_id": item.evidence_id,
            "document_name": item.document_name,
            "page_number": item.page_number,
            "chunk_id": item.chunk_id,
            "citation": item.citation,
            "content_excerpt": item.content_snapshot[:500],
        }
        for item in rows
    ]


async def validate_resource_citations(
    session: AsyncSession,
    retrieval_id: str | None,
    evidence_ids: list[str] | None,
    content: str,
) -> dict:
    issues: list[str] = []
    if retrieval_id:
        try:
            citations = await resolve_citations(
                session, retrieval_id, evidence_ids or []
            )
        except CitationValidationError as exc:
            return {"valid": False, "issues": [exc.message], "citations": []}
    else:
        citations = []
    if "中国药典" in content and not citations:
        issues.append("pharmacopoeia_claim_without_evidence")
    return {"valid": not issues, "issues": issues, "citations": citations}
