import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrations.contracts import RAGQuery
from app.integrations.mock import MockRAGProvider


async def main() -> int:
    result = await MockRAGProvider().retrieve_detailed(
        RAGQuery(query="黄芪 性状", top_k=3)
    )
    assert result.success and result.evidences
    assert all(
        item.citation and item.page_number is not None for item in result.evidences
    )
    print("V0.3B fake smoke passed: mock retrieval evidence and citations")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
