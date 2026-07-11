"""Bounded RAGFlow diagnostics; no upload, deletion, or response dumping."""

from __future__ import annotations

import argparse
import asyncio
import time

from doctor_common import Check, output, safe_exception
from app.core.config import get_settings
from app.integrations.contracts import RAGQuery
from app.integrations.factory import get_rag_provider
from app.integrations.secrets import SecretResolver


async def run(selected: set[str]) -> list[Check]:
    settings = get_settings()
    configured = bool(
        settings.ragflow_base_url
        and settings.ragflow_dataset_id
        and SecretResolver.is_configured("env:RAGFLOW_API_KEY")
    )
    if settings.rag_mode == "mock":
        provider = get_rag_provider()
        selected = (
            {"connection", "dataset", "retrieve"} if "all" in selected else selected
        )
        result: list[Check] = []
        if "connection" in selected:
            health = await provider.health_check()
            result.append(
                Check(
                    "connection",
                    "pass",
                    f"provider=mock reachable={health.get('reachable')}",
                )
            )
        if "dataset" in selected:
            result.append(Check("dataset", "pass", "mock dataset is available"))
        if "documents" in selected:
            result.append(
                Check(
                    "documents",
                    "skipped",
                    "mock provider has no external document status",
                )
            )
        if "retrieve" in selected:
            response = await provider.retrieve_detailed(
                RAGQuery(query="黄芪 性状", top_k=3)
            )
            result.append(
                Check(
                    "retrieve",
                    "pass",
                    f"provider=mock evidence={len(response.evidences)}",
                )
            )
        return result
    if not configured:
        return [
            Check(
                "ragflow",
                "skipped",
                "RAGFLOW_API_BASE_URL, RAGFLOW_API_KEY, or RAGFLOW_DATASET_ID is not configured",
            )
        ]
    provider = get_rag_provider()
    result = []
    for name in (
        {"connection", "dataset", "documents", "retrieve"}
        if "all" in selected
        else selected
    ):
        started = time.perf_counter()
        try:
            if name == "connection":
                await provider.health_check()
                detail = "reachable"
            elif name == "dataset":
                await provider.health_check()
                detail = "dataset reachable"
            elif name == "documents":
                detail = f"documents={len(await provider.list_documents())}"
            else:
                response = await provider.retrieve_detailed(
                    RAGQuery(query="中药饮片性状", top_k=3)
                )
                detail = f"evidence={len(response.evidences)} summaries={[item.citation[:80] for item in response.evidences[:3]]}"
            result.append(
                Check(
                    name,
                    "pass",
                    f"provider=ragflow elapsed_ms={round((time.perf_counter() - started) * 1000, 2)} {detail}",
                )
            )
        except Exception as exc:
            result.append(
                Check(
                    name,
                    "fail",
                    f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)} {safe_exception(exc)}",
                )
            )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", action="store_true")
    parser.add_argument("--dataset", action="store_true")
    parser.add_argument("--documents", action="store_true")
    parser.add_argument("--retrieve", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    selected = {
        name
        for name in ("connection", "dataset", "documents", "retrieve")
        if getattr(args, name)
    }
    if args.all or not selected:
        selected.add("all")
    return output(asyncio.run(run(selected)), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
