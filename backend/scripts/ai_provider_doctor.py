"""Explicit, at-most-once diagnostics for vision, generation and review providers."""

from __future__ import annotations

import argparse
import asyncio
import time

from doctor_common import Check, output, safe_exception
from app.core.config import get_settings
from app.integrations.contracts import (
    GeneratedResource,
    KnowledgeEvidence,
    ModelCallContext,
)
from app.integrations.factory import get_llm_provider, get_vision_provider
from app.integrations.mock import MockLLMProvider, MockVisionProvider
from app.integrations.secrets import SecretResolver


async def run(selected: set[str]) -> list[Check]:
    settings = get_settings()
    selected = {"vision", "generation", "review"} if "all" in selected else selected
    if settings.ai_mode != "mock" and not settings.real_ai_tests_enabled:
        return [
            Check(
                "ai_provider",
                "skipped",
                "REAL_AI_TESTS_ENABLED=true is required before real API calls",
            )
        ]
    if (
        settings.ai_mode != "mock"
        and not (settings.model_api_base_url or settings.llm_base_url)
        or (
            settings.ai_mode != "mock"
            and not (
                SecretResolver.is_configured("env:MODEL_API_KEY")
                or SecretResolver.is_configured("env:LLM_API_KEY")
            )
        )
    ):
        return [
            Check(
                "ai_provider",
                "skipped",
                "real model base URL or API key is not configured",
            )
        ]
    result: list[Check] = []
    evidence = [
        KnowledgeEvidence(
            chunk_id="doctor_chunk",
            content="黄芪为教学示例，不构成处方建议。",
            document_name="demo",
            page=1,
            score=1,
            source_type="mock",
        )
    ]
    for name in selected:
        started = time.perf_counter()
        try:
            if name == "vision":
                provider = (
                    MockVisionProvider()
                    if settings.ai_mode == "mock"
                    else get_vision_provider()
                )
                if settings.ai_mode != "mock":
                    raise RuntimeError(
                        "vision doctor requires --image through full-loop smoke"
                    )
                value = await provider.recognize(
                    None, ModelCallContext(agent_code="doctor_vision")
                )
                detail = f"provider={value.provider} candidates={len(value.top_candidates)} confidence={value.candidate.confidence if value.candidate else None}"
            elif name == "generation":
                provider = (
                    MockLLMProvider()
                    if settings.ai_mode == "mock"
                    else get_llm_provider()
                )
                value = await provider.generate_resource(
                    evidence, ModelCallContext(agent_code="doctor_generation")
                )
                detail = f"resources={len(value)} provider={'mock' if settings.ai_mode == 'mock' else 'configured'}"
            else:
                provider = (
                    MockLLMProvider()
                    if settings.ai_mode == "mock"
                    else get_llm_provider()
                )
                value = await provider.review_resource(
                    [GeneratedResource(title="最小教学资源", content="仅作教学示例。")],
                    ModelCallContext(agent_code="doctor_review"),
                )
                detail = f"status={value.status} provider={'mock' if settings.ai_mode == 'mock' else 'configured'}"
            result.append(
                Check(
                    name,
                    "pass",
                    f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)} {detail}",
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
    parser.add_argument("--vision", action="store_true")
    parser.add_argument("--generation", action="store_true")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    selected = {
        name for name in ("vision", "generation", "review") if getattr(args, name)
    }
    if args.all or not selected:
        selected.add("all")
    return output(asyncio.run(run(selected)), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
