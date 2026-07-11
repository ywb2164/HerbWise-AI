"""Generate UTF-8 frontend mock envelopes matching the common API response."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOCK_DIR = ROOT / "docs" / "mock"
ENVELOPE = {"code": 0, "message": "success", "request_id": "req_mock_v02"}


def write(name: str, data: object) -> None:
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    (MOCK_DIR / name).write_text(
        json.dumps({**ENVELOPE, "data": data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    write(
        "auth-login.json",
        {
            "access_token": "mock.access.token",
            "refresh_token": "mock.refresh.token",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": 1,
                "username": "admin",
                "display_name": "System administrator",
                "roles": ["admin"],
                "permissions": ["*"],
            },
        },
    )
    write(
        "profile.json",
        {
            "learner_id": "stu_001",
            "name": "Demo learner",
            "identity_type": "student",
            "overall_level": "basic",
        },
    )
    write(
        "profile-dimensions.json",
        [
            {
                "dimension_code": "basic_knowledge",
                "score": 50,
                "level": "weak",
                "evidence_json": {"seed": "demo_seed_data"},
            }
        ],
    )
    write(
        "medicine.json",
        {
            "id": 1,
            "medicine_code": "astragalus",
            "standard_name_zh": "黄芪",
            "standard_name_en": "Astragalus",
            "matched_by": "standard_name_zh",
        },
    )
    write("task.json", {"task_id": "task_mock", "status": "success", "progress": 100})
    write(
        "task-events.json",
        [
            {
                "event": "node_completed",
                "task_id": "task_mock",
                "node": "save_trace",
                "status": "success",
                "progress": 100,
            }
        ],
    )
    write(
        "resource.json",
        {
            "resource_id": "res_mock",
            "resource_type": "lecture",
            "status": "generated",
            "provider": "mock",
        },
    )
    write(
        "review.json",
        {
            "review_id": "review_mock",
            "resource_id": "res_mock",
            "status": "pass",
            "provider": "mock",
        },
    )
    write(
        "learning-path.json",
        {
            "learner_id": "stu_001",
            "version": 1,
            "status": "active",
            "current_stage": "foundation",
        },
    )
    write(
        "trace.json",
        {
            "trace_id": "trace_mock",
            "task_id": "task_mock",
            "learner_id": "stu_001",
            "trace_data": {"data_source": "mock"},
        },
    )
    write(
        "metrics.json",
        {
            "learner_count": 1,
            "medicine_count": 3,
            "data_source": "mixed",
            "is_official": False,
        },
    )
    write(
        "vision-qwen-result.json",
        {
            "provider": "qwen",
            "model_name": "qwen-vl-demo",
            "candidate": {"medicine_id": 1, "herb_name": "黄芪", "confidence": 0.81},
            "top_candidates": [],
            "data_source": "real",
        },
    )
    write(
        "vision-local-result.json",
        {
            "provider": "local",
            "model_name": "demo.pt",
            "candidate": {"medicine_id": 1, "herb_name": "黄芪", "confidence": 0.78},
            "top_candidates": [],
            "data_source": "local",
        },
    )
    write(
        "vision-fusion-agree.json",
        {
            "agreement_status": "agree",
            "confidence_before_adjustment": 0.81,
            "confidence_after_adjustment": 0.96,
            "manual_review_required": False,
            "rule_version": "v0.3a-fusion-v1",
        },
    )
    write(
        "vision-fusion-conflict.json",
        {
            "agreement_status": "conflict",
            "confidence_before_adjustment": 0.78,
            "confidence_after_adjustment": 0.63,
            "manual_review_required": True,
            "rule_version": "v0.3a-fusion-v1",
        },
    )
    write(
        "model-call-record.json",
        {
            "call_id": "mcall_mock",
            "provider": "qwen",
            "model_name": "qwen-vl-demo",
            "call_type": "vision_qwen",
            "success": True,
            "latency_ms": 420.0,
            "total_tokens": 123,
        },
    )


if __name__ == "__main__":
    main()
