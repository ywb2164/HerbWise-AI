"""Run one explicitly configured RAG retrieval and print safe citation summaries."""

from __future__ import annotations
import argparse
import asyncio
from doctor_common import Check, output
from app.core.config import get_settings
from app.integrations.contracts import RAGQuery
from app.integrations.factory import get_rag_provider
from app.integrations.secrets import SecretResolver


async def run(medicine: str, query: str) -> list[Check]:
    settings = get_settings()
    if not (
        settings.ragflow_base_url
        and settings.ragflow_dataset_id
        and SecretResolver.is_configured("env:RAGFLOW_API_KEY")
    ):
        return [
            Check(
                "citation_verification", "skipped", "RAGFlow configuration is missing"
            )
        ]
    result = await get_rag_provider().retrieve_detailed(
        RAGQuery(query=f"{medicine} {query}", top_k=3)
    )
    valid = [
        item
        for item in result.evidences
        if item.document_id and item.chunk_id and item.citation
    ]
    return [
        Check(
            "citation_verification",
            "pass" if len(valid) == len(result.evidences) else "fail",
            f"evidence={len(result.evidences)} valid={len(valid)} citations={[item.citation[:120] for item in valid]}",
        )
    ]


parser = argparse.ArgumentParser()
parser.add_argument("medicine")
parser.add_argument("query")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()
raise SystemExit(output(asyncio.run(run(args.medicine, args.query)), args.json))
