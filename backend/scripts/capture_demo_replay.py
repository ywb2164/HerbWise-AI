"""Capture a completed task's successful retrieval as an explicit replay snapshot."""

from __future__ import annotations
import argparse
import asyncio
from sqlalchemy import select
from app.common.ids import new_id
from app.core.database import async_session_factory
from app.modules.knowledge.rag_models import (
    RAGEvidenceRecord,
    RAGReplayRecord,
    RAGRetrievalRecord,
)
from app.modules.tasks.models import TaskRecord


async def capture(task_id: str) -> dict[str, object]:
    async with async_session_factory() as session:
        task = await session.scalar(
            select(TaskRecord).where(TaskRecord.task_id == task_id)
        )
        if task is None or task.status != "success":
            raise ValueError("only a successful task can be captured")
        retrieval = await session.scalar(
            select(RAGRetrievalRecord)
            .where(
                RAGRetrievalRecord.task_id == task_id,
                RAGRetrievalRecord.status == "success",
            )
            .order_by(RAGRetrievalRecord.id.desc())
        )
        if retrieval is None:
            raise ValueError("successful task has no retrieval to capture")
        evidence = list(
            (
                await session.scalars(
                    select(RAGEvidenceRecord).where(
                        RAGEvidenceRecord.retrieval_id == retrieval.retrieval_id
                    )
                )
            ).all()
        )
        if not evidence:
            raise ValueError("retrieval has no evidence to capture")
        snapshot = [
            {
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "document_name": item.document_name,
                "chunk_id": item.chunk_id,
                "page_number": item.page_number,
                "content": item.content_snapshot,
                "score": item.score,
                "source_type": "replay",
                "citation": item.citation,
                "metadata": item.metadata_json or {},
                "data_source": "replay",
                "rank": item.rank,
            }
            for item in evidence
        ]
        existing = await session.scalar(
            select(RAGReplayRecord).where(
                RAGReplayRecord.source_retrieval_id == retrieval.retrieval_id
            )
        )
        if existing is None:
            existing = RAGReplayRecord(
                replay_code=new_id("replay"),
                query_fingerprint=__import__("hashlib")
                .sha256(f"{retrieval.query}|8|0.25".encode())
                .hexdigest(),
                evidence_snapshot_json=snapshot,
                source_retrieval_id=retrieval.retrieval_id,
                medicine_id=retrieval.medicine_id,
                task_type="identification",
                is_active=True,
            )
            session.add(existing)
            await session.commit()
        return {
            "replay_code": existing.replay_code,
            "source_retrieval_id": retrieval.retrieval_id,
            "evidence_count": len(existing.evidence_snapshot_json),
        }


parser = argparse.ArgumentParser()
parser.add_argument("task_id")
args = parser.parse_args()
print(asyncio.run(capture(args.task_id)))
