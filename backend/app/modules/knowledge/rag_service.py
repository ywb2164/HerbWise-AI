from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.core.config import get_settings
from app.integrations.contracts import RAGEvidence, RAGQuery, RAGRetrievalResult
from app.integrations.factory import get_rag_provider
from app.modules.knowledge.models import MedicineFeature, MedicineItem
from app.modules.knowledge.rag_models import (
    RAGEvidenceRecord,
    RAGReplayRecord,
    RAGRetrievalRecord,
)


class KnowledgeQueryBuilder:
    version = "query_builder_v1"

    def build(
        self,
        medicine: MedicineItem | None,
        task_type: str,
        user_query: str | None = None,
    ) -> str:
        parts = [
            medicine.standard_name_zh if medicine else "",
            medicine.standard_name_en if medicine and medicine.standard_name_en else "",
            "中药饮片",
            "性状 切面 质控",
            task_type,
            user_query or "",
        ]
        seen: set[str] = set()
        values = []
        for part in parts:
            clean = re.sub(r"\s+", " ", part).strip()
            if clean and clean not in seen:
                values.append(clean)
                seen.add(clean)
        return " ".join(values)[:500]


def _fingerprint(query: RAGQuery) -> str:
    return hashlib.sha256(
        f"{query.query}|{query.top_k}|{query.score_threshold}".encode()
    ).hexdigest()


def _rank(evidences: list[RAGEvidence]) -> list[RAGEvidence]:
    seen: dict[str, RAGEvidence] = {}
    for item in evidences:
        key = (
            item.chunk_id
            or hashlib.sha256(re.sub(r"\s+", " ", item.content).encode()).hexdigest()
        )
        previous = seen.get(key)
        if previous is None or item.score > previous.score:
            seen[key] = item
    ordered = sorted(
        seen.values(),
        key=lambda item: (
            item.source_type != "structured",
            -item.score,
            item.document_name,
        ),
    )
    return [
        item.model_copy(
            update={
                "rank": index,
                "retained_reason": "structured_priority"
                if item.source_type == "structured"
                else "score_ranked",
            }
        )
        for index, item in enumerate(ordered, start=1)
    ]


def _truncate(
    evidences: list[RAGEvidence], max_items: int, max_chars: int
) -> list[RAGEvidence]:
    result: list[RAGEvidence] = []
    used = 0
    for item in evidences[:max_items]:
        available = max_chars - used
        if available <= 0:
            break
        content = item.content
        if len(content) > available:
            cutoff = content.rfind("。", 0, available)
            content = content[: cutoff + 1 if cutoff > 0 else available]
        result.append(item.model_copy(update={"content": content}))
        used += len(content)
    return result


class HybridKnowledgeService:
    async def retrieve(
        self, session: AsyncSession, query: RAGQuery
    ) -> tuple[str, RAGRetrievalResult]:
        settings = get_settings()
        retrieval_id = new_id("retrieval")
        medicine = (
            await session.get(MedicineItem, query.medicine_id)
            if query.medicine_id
            else None
        )
        structured: list[RAGEvidence] = []
        if medicine:
            features = list(
                (
                    await session.scalars(
                        select(MedicineFeature).where(
                            MedicineFeature.medicine_id == medicine.id
                        )
                    )
                ).all()
            )
            structured = [
                RAGEvidence(
                    evidence_id=f"structured_{feature.id}",
                    medicine_id=medicine.id,
                    document_name=medicine.standard_name_zh,
                    chunk_id=f"feature_{feature.id}",
                    content=f"{feature.feature_name}：{feature.feature_value}",
                    score=1,
                    source_type="structured",
                    citation=f"{medicine.standard_name_zh} structured feature [{feature.id}]",
                    data_source="structured",
                )
                for feature in features
            ]
        replay_used = False
        fallback = False
        remote = RAGRetrievalResult(
            success=True,
            query=query.query,
            provider="structured",
            data_source="structured",
        )
        if settings.rag_mode == "replay":
            row = await session.scalar(
                select(RAGReplayRecord).where(
                    RAGReplayRecord.query_fingerprint == _fingerprint(query),
                    RAGReplayRecord.is_active.is_(True),
                )
            )
            if row:
                remote = RAGRetrievalResult(
                    success=True,
                    query=query.query,
                    provider="replay",
                    evidences=[
                        RAGEvidence.model_validate(item)
                        for item in row.evidence_snapshot_json
                    ],
                    returned_count=len(row.evidence_snapshot_json),
                    replay_used=True,
                    data_source="replay",
                )
                replay_used = True
        elif settings.rag_mode in {"mock", "ragflow", "hybrid"}:
            try:
                remote = await get_rag_provider().retrieve_detailed(query)
            except Exception as exc:
                if settings.rag_mode in {"hybrid", "mock"}:
                    remote = (
                        await __import__(
                            "app.integrations.mock", fromlist=["MockRAGProvider"]
                        )
                        .MockRAGProvider()
                        .retrieve_detailed(query)
                    )
                    fallback = True
                else:
                    remote = RAGRetrievalResult(
                        success=False,
                        query=query.query,
                        provider="ragflow",
                        error_code=getattr(exc, "error_code", "provider_unavailable"),
                        error_message=str(exc),
                        fallback_used=True,
                        data_source="ragflow",
                    )
        merged = _truncate(
            _rank(
                structured
                + [
                    item
                    for item in remote.evidences
                    if item.score >= query.score_threshold
                ]
            ),
            settings.rag_max_evidence_items,
            settings.rag_max_evidence_characters,
        )
        result = remote.model_copy(
            update={
                "evidences": merged,
                "returned_count": len(merged),
                "fallback_used": fallback,
                "replay_used": replay_used,
                "data_source": "hybrid"
                if structured and remote.evidences
                else remote.data_source,
                "retrieval_metadata": {
                    "query_version": KnowledgeQueryBuilder.version,
                    "structured_count": len(structured),
                    "rag_count": len(remote.evidences),
                    "insufficient_evidence": not bool(merged),
                },
            }
        )
        session.add(
            RAGRetrievalRecord(
                retrieval_id=retrieval_id,
                task_id=query.task_id,
                learner_id=query.learner_id,
                query=query.query,
                provider=result.provider,
                dataset_id=result.dataset_id,
                medicine_id=query.medicine_id,
                returned_count=len(merged),
                latency_ms=result.latency_ms,
                cache_hit=False,
                replay_used=replay_used,
                fallback_used=fallback,
                status="success" if result.success else "failed",
                error_code=result.error_code,
                error_message=result.error_message,
                metadata_json=result.retrieval_metadata,
            )
        )
        for evidence in merged:
            session.add(
                RAGEvidenceRecord(
                    retrieval_id=retrieval_id,
                    evidence_id=evidence.evidence_id,
                    document_id=evidence.document_id,
                    chunk_id=evidence.chunk_id,
                    document_name=evidence.document_name,
                    page_number=evidence.page_number,
                    content_snapshot=evidence.content[:4000],
                    score=evidence.score,
                    citation=evidence.citation,
                    metadata_json=evidence.metadata,
                )
            )
        await session.commit()
        return retrieval_id, result
