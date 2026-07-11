import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.integrations.contracts import RAGQuery
from app.integrations.mock import MockRAGProvider
from app.integrations.rag.ragflow import RAGFlowProvider


async def run(mode: str) -> dict:
    if mode == "real":
        s = get_settings()
        if not (
            s.real_rag_tests_enabled
            and s.ragflow_base_url
            and s.ragflow_dataset_id
            and s.ragflow_api_key.get_secret_value()
        ):
            return {"status": "SKIPPED"}
        provider = RAGFlowProvider()
    else:
        provider = MockRAGProvider()
    cases = [
        "黄芪性状",
        "黄芪切面",
        "黄芪党参辨析",
        "甘草性状",
        "甘草切面",
        "炮制特征",
        "质控信息",
        "未收录药材",
        "证据不足",
        "无效查询",
    ]
    results = [await provider.retrieve_detailed(RAGQuery(query=item)) for item in cases]
    count = len(results)
    success = sum(item.success for item in results)
    evidence = sum(bool(item.evidences) for item in results)
    return {
        "data_source": "demo" if mode == "fake" else "real_demo",
        "is_official": False,
        "total_cases": count,
        "successful_cases": success,
        "retrieval_success_rate": success / count,
        "evidence_presence_rate": evidence / count,
        "citation_completeness_rate": sum(
            all(e.citation for e in item.evidences) for item in results
        )
        / count,
        "expected_document_hit_rate": 0.0,
        "expected_medicine_hit_rate": 0.0,
        "insufficient_evidence_accuracy": 0.0,
        "average_latency_ms": sum(item.latency_ms for item in results) / count,
        "cache_hit_rate": 0.0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fake", "real"], default="fake")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = asyncio.run(run(args.mode))
    print(json.dumps(result, ensure_ascii=False))
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
