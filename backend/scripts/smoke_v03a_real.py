"""Opt-in, bounded real-provider smoke test.

It is intentionally skipped unless every required environment setting is
present. The script does not print secrets, prompts, or image bytes.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.integrations.contracts import ModelCallContext
from app.integrations.vision.qwen import QwenVisionProvider


async def main() -> int:
    settings = get_settings()
    image = os.getenv("REAL_AI_TEST_IMAGE", "")
    if not (
        settings.real_ai_tests_enabled
        and settings.model_api_key.get_secret_value()
        and settings.qwen_vl_model
        and image
    ):
        print(
            "SKIPPED: REAL_AI_TESTS_ENABLED, MODEL_API_KEY, QWEN_VL_MODEL, and REAL_AI_TEST_IMAGE are required"
        )
        return 0
    if not Path(image).is_file():
        print("SKIPPED: REAL_AI_TEST_IMAGE does not exist")
        return 0
    result = await QwenVisionProvider().recognize(
        image, ModelCallContext(agent_code="real_smoke", file_id="real_smoke")
    )
    print(
        {
            "provider": result.provider,
            "model": result.model_name,
            "elapsed_ms": result.elapsed_ms,
            "candidate": result.candidate.herb_name if result.candidate else None,
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f"smoke_v03a_real failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
