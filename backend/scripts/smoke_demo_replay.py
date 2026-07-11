"""Offline replay contract smoke. It deliberately makes no network or DB call."""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.integrations.contracts import RAGEvidence, RAGRetrievalResult


async def main() -> int:
    evidence = RAGEvidence(
        evidence_id="demo_replay_1",
        document_id="demo_doc",
        document_name="授权演示资料",
        chunk_id="demo_chunk",
        page_number=1,
        content="离线演示证据。",
        score=0.9,
        source_type="replay",
        citation="授权演示资料 p.1 [demo_chunk]",
        data_source="replay",
        rank=1,
    )
    response = RAGRetrievalResult(
        success=True,
        query="离线演示",
        provider="replay",
        evidences=[evidence],
        returned_count=1,
        replay_used=True,
        data_source="replay",
    )
    assert (
        response.replay_used
        and response.evidences[0].citation
        and response.data_source == "replay"
    )
    print(
        "Replay smoke passed: offline replay evidence, citation, and source marker verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
