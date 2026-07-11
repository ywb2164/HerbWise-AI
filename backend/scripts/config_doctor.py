"""Inspect local HerbWise configuration without exposing secrets."""

from __future__ import annotations

import argparse
import platform
from pathlib import Path

from doctor_common import Check, configured, output, writable
from app.core.config import get_settings
from app.integrations.secrets import SecretResolver


def checks(scope: str) -> list[Check]:
    settings = get_settings()
    result = [
        Check("python", "pass", platform.python_version()),
        Check("project_path", "pass", str(Path(__file__).resolve().parents[1])),
        Check(
            "settings",
            "pass",
            f"APP_ENV={settings.app_env}; RUN_MODE={settings.run_mode}",
        ),
        Check(
            "mysql",
            "pass" if configured(settings.database_url) else "fail",
            "configured"
            if configured(settings.database_url)
            else "DATABASE_URL is required",
        ),
        Check(
            "redis",
            "pass" if configured(settings.redis_url) else "fail",
            "configured" if configured(settings.redis_url) else "REDIS_URL is required",
        ),
    ]
    if scope in {"ai", "all"}:
        key = SecretResolver.is_configured(
            "env:MODEL_API_KEY"
        ) or SecretResolver.is_configured("env:LLM_API_KEY")
        active = (
            settings.ai_mode != "mock"
            or settings.llm_mode == "real"
            or settings.effective_vision_mode() == "qwen"
        )
        result.extend(
            [
                Check(
                    "model_api_base_url",
                    "pass"
                    if configured(settings.model_api_base_url or settings.llm_base_url)
                    else ("warning" if not active else "fail"),
                    "configured"
                    if configured(settings.model_api_base_url or settings.llm_base_url)
                    else "not configured",
                ),
                Check(
                    "model_api_key",
                    "pass" if key else ("warning" if not active else "fail"),
                    f"configured={key}",
                ),
                Check(
                    "qwen_vl_model",
                    "pass" if configured(settings.qwen_vl_model) else "warning",
                    settings.qwen_vl_model or "not configured",
                ),
                Check(
                    "generation_model",
                    "pass"
                    if configured(settings.generation_model or settings.text_model)
                    else "warning",
                    settings.generation_model
                    or settings.text_model
                    or "not configured",
                ),
                Check(
                    "review_model",
                    "pass" if configured(settings.review_model) else "warning",
                    settings.review_model or "not configured",
                ),
            ]
        )
    if scope in {"ragflow", "all"}:
        active = settings.rag_mode in {"ragflow", "hybrid"}
        rag_key = SecretResolver.is_configured("env:RAGFLOW_API_KEY")
        result.extend(
            [
                Check(
                    "ragflow_base_url",
                    "pass"
                    if configured(settings.ragflow_base_url)
                    else ("warning" if not active else "fail"),
                    "configured"
                    if configured(settings.ragflow_base_url)
                    else "not configured",
                ),
                Check(
                    "ragflow_api_key",
                    "pass" if rag_key else ("warning" if not active else "fail"),
                    f"configured={rag_key}",
                ),
                Check(
                    "ragflow_dataset_id",
                    "pass"
                    if configured(settings.ragflow_dataset_id)
                    else ("warning" if not active else "fail"),
                    settings.ragflow_dataset_id or "not configured",
                ),
            ]
        )
    if scope in {"local-model", "all"}:
        model = Path(settings.local_model_path) if settings.local_model_path else None
        result.append(
            Check(
                "local_model",
                "pass"
                if settings.local_vision_enabled and model and model.is_file()
                else "skipped"
                if not settings.local_vision_enabled
                else "fail",
                "disabled"
                if not settings.local_vision_enabled
                else "file exists"
                if model and model.is_file()
                else "LOCAL_MODEL_PATH does not point to a file",
            )
        )
    for name, path in (
        ("upload_directory", settings.upload_dir),
        ("report_directory", settings.effective_report_dir()),
    ):
        ok, detail = writable(path)
        result.append(Check(name, "pass" if ok else "warning", detail))
    result.append(
        Check(
            "replay",
            "pass"
            if settings.demo_replay_enabled and settings.rag_replay_enabled
            else "warning",
            "enabled"
            if settings.demo_replay_enabled and settings.rag_replay_enabled
            else "disabled",
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--check", choices=["ragflow", "ai", "local-model", "all"], default="all"
    )
    args = parser.parse_args()
    return output(checks(args.check), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
