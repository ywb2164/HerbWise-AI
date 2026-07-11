import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.integrations.contracts import RAGQuery
from app.integrations.rag.ragflow import RAGFlowProvider


async def main() -> int:
    settings = get_settings()
    if not (
        settings.real_rag_tests_enabled
        and settings.ragflow_base_url
        and settings.ragflow_dataset_id
        and settings.ragflow_api_key.get_secret_value()
    ):
        print("SKIPPED: REAL_RAG_TESTS_ENABLED and RAGFlow configuration are required")
        return 0
    result = await RAGFlowProvider().retrieve_detailed(
        RAGQuery(query="中药饮片 性状", top_k=1)
    )
    print(
        {
            "provider": result.provider,
            "latency_ms": result.latency_ms,
            "returned_count": result.returned_count,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
