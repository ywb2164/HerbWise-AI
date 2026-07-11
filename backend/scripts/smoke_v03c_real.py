"""Gated real/hybrid full-loop preflight; it never enables paid services implicitly."""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.integrations.secrets import SecretResolver


async def main() -> int:
    s = get_settings()
    configured = bool(
        s.real_full_loop_tests_enabled
        and s.demo_test_image_path
        and Path(s.demo_test_image_path).is_file()
        and s.ragflow_base_url
        and s.ragflow_dataset_id
        and SecretResolver.is_configured("env:RAGFLOW_API_KEY")
        and (s.model_api_base_url or s.llm_base_url)
        and (
            SecretResolver.is_configured("env:MODEL_API_KEY")
            or SecretResolver.is_configured("env:LLM_API_KEY")
        )
    )
    if not configured:
        print(
            "SKIPPED: set REAL_FULL_LOOP_TESTS_ENABLED=true plus test image, RAGFlow, and model credentials"
        )
        return 0
    print(
        "SKIPPED: real HTTP full-loop is intentionally run through the documented user-local command after service startup"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
