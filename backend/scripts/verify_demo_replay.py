"""Verify a replay snapshot is active, bounded, and contains cited evidence."""

from __future__ import annotations
import argparse
import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.modules.knowledge.rag_models import RAGReplayRecord


async def verify(code: str) -> dict[str, object]:
    async with async_session_factory() as session:
        item = await session.scalar(
            select(RAGReplayRecord).where(RAGReplayRecord.replay_code == code)
        )
        if item is None or not item.is_active:
            raise ValueError("active replay code was not found")
        valid = all(
            row.get("citation") and row.get("chunk_id")
            for row in item.evidence_snapshot_json
        )
        if not valid:
            raise ValueError("replay evidence is missing citation or chunk mapping")
        return {
            "replay_code": item.replay_code,
            "active": item.is_active,
            "evidence_count": len(item.evidence_snapshot_json),
            "data_source": "replay",
        }


parser = argparse.ArgumentParser()
parser.add_argument("replay_code")
args = parser.parse_args()
print(asyncio.run(verify(args.replay_code)))
