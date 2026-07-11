"""Inspect a configured local vision model without loading it at API startup."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import time
from pathlib import Path

from doctor_common import Check, output, safe_exception
from app.core.config import get_settings
from app.integrations.contracts import ModelCallContext
from app.integrations.vision.local import UltralyticsLocalVisionProvider


def model_checks() -> list[Check]:
    settings = get_settings()
    if not settings.local_vision_enabled:
        return [Check("local_model", "skipped", "LOCAL_VISION_ENABLED=false")]
    path = Path(settings.local_model_path)
    if not path.is_file():
        return [
            Check(
                "local_model",
                "fail",
                "LOCAL_MODEL_PATH does not point to a readable model file",
            )
        ]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return [
        Check(
            "local_model",
            "pass",
            f"model_type={settings.local_model_type} file_exists=true file_size={path.stat().st_size} sha256={digest} device={settings.local_model_device}",
        )
    ]


async def load_or_predict(image: str | None) -> list[Check]:
    base = model_checks()
    if base[0].status != "pass":
        return base
    started = time.perf_counter()
    try:
        provider = UltralyticsLocalVisionProvider()
        if image:
            result = await provider.predict_image(
                image, ModelCallContext(agent_code="doctor_local_model")
            )
            labels = [
                (item.herb_name, round(item.confidence, 4))
                for item in result.top_candidates[:3]
            ]
            base.append(
                Check(
                    "predict",
                    "pass",
                    f"load_time_ms={round((time.perf_counter() - started) * 1000, 2)} top3={labels}",
                )
            )
        else:
            await asyncio.to_thread(
                provider._load
            )  # bounded, lazy loader used by production provider
            status = provider.status()
            base.append(
                Check(
                    "load",
                    "pass",
                    f"load_time_ms={status.get('load_ms')} class_count=available_after_predict",
                )
            )
    except Exception as exc:
        base.append(Check("predict" if image else "load", "fail", safe_exception(exc)))
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--info", action="store_true")
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--predict")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.predict and not Path(args.predict).is_file():
        return output(
            [Check("predict", "fail", "image path does not exist")], args.json
        )
    checks = (
        asyncio.run(load_or_predict(args.predict))
        if args.load or args.predict
        else model_checks()
    )
    return output(checks, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
