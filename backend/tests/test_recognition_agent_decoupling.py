from app.core.config import Settings
from app.modules.recognition.agent_advice import _advice_from_snapshot
from app.modules.recognition.models import RecognitionRecord
from app.modules.recognition.service import record_data


def _record(*, catalog_status: str = "matched") -> RecognitionRecord:
    return RecognitionRecord(
        recognition_id="recognition_test",
        task_id=None,
        learner_id="stu_001",
        file_id="file_test",
        vision_mode="fixed_pipeline",
        status="success",
        final_name="川芎",
        confidence=0.93,
        agreement_status="agree",
        manual_review_required=False,
        data_source="real",
        fusion_result_json={
            "final_identification": {
                "display_name_zh": "川芎",
                "standard_name_zh": "川芎" if catalog_status == "matched" else None,
                "name_en": "Chuanxiong Rhizome",
                "confidence": 0.93,
                "catalog_status": catalog_status,
            }
        },
    )


def test_recognition_response_is_complete_without_agent() -> None:
    data = record_data(_record())
    assert data["status"] == "success"
    assert data["recognition_status"] == "completed"
    assert data["final_identification"]["display_name_zh"] == "川芎"


def test_agent_advice_uses_snapshot_without_changing_identification() -> None:
    record = _record(catalog_status="out_of_catalog")
    before = record.fusion_result_json.copy()
    advice = _advice_from_snapshot(record)
    assert advice["learning_dimension"] == "appearance_identification"
    assert record.fusion_result_json == before
    assert advice["recommended_actions"][1]["type"] == "capture_clearer_image"


def test_agent_mode_defaults_to_manual_and_legacy_full_loop_is_disabled() -> None:
    settings = Settings()
    assert settings.recognition_agent_mode == "manual"
    assert settings.recognition_use_legacy_full_loop is False
