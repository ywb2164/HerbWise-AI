"""Offline V0.3A smoke test; it never invokes a billable provider."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrations.contracts import (
    GeneratedResource,
    RecognitionCandidate,
    VisionRecognitionResult,
)
from app.integrations.mock import MockLLMProvider
from app.modules.recognition.fusion import fuse_recognition


async def main() -> int:
    local_candidate = RecognitionCandidate(
        medicine_id=1, herb_name="黄芪", confidence=0.8, in_supported_catalog=True
    )
    qwen_candidate = RecognitionCandidate(
        medicine_id=1, herb_name="黄芪", confidence=0.78, in_supported_catalog=True
    )
    fusion = fuse_recognition(
        VisionRecognitionResult(
            provider="fake-local",
            candidate=local_candidate,
            top_candidates=[local_candidate],
        ),
        VisionRecognitionResult(
            provider="fake-qwen",
            candidate=qwen_candidate,
            top_candidates=[qwen_candidate],
        ),
    )
    if fusion.agreement_status != "agree" or fusion.final_candidate is None:
        raise RuntimeError("fake hybrid fusion failed")
    provider = MockLLMProvider()
    review = await provider.review_resource(
        [
            GeneratedResource(
                title="Fake resource", content="Fake evidence-backed resource"
            )
        ]
    )
    if review.status != "pass":
        raise RuntimeError("fake review failed")
    print("V0.3A fake smoke passed: hybrid agreement, mock resource review")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f"smoke_v03a_fake failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
