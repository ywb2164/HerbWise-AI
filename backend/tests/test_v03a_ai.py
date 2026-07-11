import importlib

import pytest

from app.core.config import get_settings
from app.integrations.contracts import RecognitionCandidate, VisionRecognitionResult
from app.integrations.openai_compatible import extract_json
from app.integrations.secrets import SecretConfigurationError, SecretResolver
from app.modules.knowledge.normalizer import normalize_name
from app.modules.recognition.fusion import fuse_recognition


def _vision(
    *, medicine_id: int | None, name: str, confidence: float, catalog: bool = True
) -> VisionRecognitionResult:
    candidate = RecognitionCandidate(
        medicine_id=medicine_id,
        herb_name=name,
        confidence=confidence,
        in_supported_catalog=catalog,
    )
    return VisionRecognitionResult(
        provider="fake", candidate=candidate, top_candidates=[candidate]
    )


def test_name_normalization_is_lightweight_and_not_fuzzy() -> None:
    assert normalize_name(" Astragalus (root) ") == "astragalusroot"
    assert normalize_name("黄 芪") == "黄芪"
    assert normalize_name("黄芪") != normalize_name("党参")


def test_fusion_agreement_bonus_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "fusion_agreement_bonus", 0.15)
    monkeypatch.setattr(settings, "fusion_confidence_cap", 0.99)
    result = fuse_recognition(
        _vision(medicine_id=1, name="黄芪", confidence=0.95),
        _vision(medicine_id=1, name="黄芪", confidence=0.90),
    )
    assert result.agreement_status == "agree"
    assert result.confidence_after_adjustment == 0.99
    assert result.manual_review_required is False


def test_fusion_conflict_prefers_local_conservatively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "fusion_conflict_penalty", 0.15)
    result = fuse_recognition(
        _vision(medicine_id=1, name="黄芪", confidence=0.9),
        _vision(medicine_id=2, name="党参", confidence=0.9),
    )
    assert result.agreement_status == "conflict"
    assert result.confidence_after_adjustment == 0.75
    assert result.manual_review_required is True


def test_out_of_catalog_qwen_falls_back_to_valid_local() -> None:
    result = fuse_recognition(
        _vision(medicine_id=1, name="黄芪", confidence=0.8),
        _vision(medicine_id=None, name="未知", confidence=0.95, catalog=False),
    )
    assert result.final_candidate is not None
    assert result.final_candidate.herb_name == "黄芪"
    assert result.manual_review_required is True


def test_one_provider_and_no_provider_fallbacks() -> None:
    local = _vision(medicine_id=1, name="黄芪", confidence=0.7)
    assert fuse_recognition(local, None).agreement_status == "local_only"
    assert fuse_recognition(None, None).final_candidate is None


def test_openai_json_extraction_accepts_markdown_fences() -> None:
    assert extract_json('```json\n{"status": "pass"}\n```') == {"status": "pass"}
    with pytest.raises(ValueError):
        extract_json("not json")


def test_secret_resolver_requires_env_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("V03A_TEST_SECRET", raising=False)
    with pytest.raises(SecretConfigurationError):
        SecretResolver.resolve("env:V03A_TEST_SECRET")
    monkeypatch.setenv("V03A_TEST_SECRET", "not-exposed")
    assert SecretResolver.is_configured("env:V03A_TEST_SECRET")


def test_v03a_migration_only_creates_new_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = importlib.import_module(
        "migrations.versions.7a3e91b4c2f0_add_real_ai_integration_records"
    )
    created: list[str] = []
    monkeypatch.setattr(migration, "_tables", lambda: set())
    monkeypatch.setattr(
        migration.op, "create_table", lambda name, *_args: created.append(name)
    )
    migration.upgrade()
    assert set(created) == {"model_call_records", "recognition_records"}
