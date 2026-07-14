from app.integrations.contracts import RecognitionCandidate, VisionRecognitionResult
from app.modules.knowledge.catalog import KnowledgeCatalog
from app.modules.recognition.fusion import fuse_recognition
from app.modules.recognition.service import _knowledge_verification


def _vision(
    name: str, confidence: float, *, material_type: str = "plant_rhizome"
) -> VisionRecognitionResult:
    candidate = RecognitionCandidate(
        herb_name=name,
        english_name=name,
        raw_name=name,
        confidence=confidence,
        in_supported_catalog=False,
    )
    return VisionRecognitionResult(
        provider="fake",
        candidate=candidate,
        top_candidates=[candidate],
        material_type=material_type,
    )


def test_catalog_uses_exact_normalized_names_and_aliases() -> None:
    assert KnowledgeCatalog.status()["loaded"] is True
    assert KnowledgeCatalog.match(name_zh="茯苓", name_en="Poria").status == "matched"
    assert (
        KnowledgeCatalog.match(name_zh=None, name_en="white-peony root").status
        == "matched"
    )
    assert (
        KnowledgeCatalog.match(name_zh="全蝎", name_en="Scorpion").status
        == "out_of_catalog"
    )
    assert (
        KnowledgeCatalog.match(name_zh=None, name_en="Rehmannia").status
        == "out_of_catalog"
    )


def test_primary_qwen_unavailable_never_promotes_yolo() -> None:
    result = fuse_recognition(_vision("Prepared Rehmannia", 0.87), None)
    assert result.status == "primary_recognition_unavailable"
    assert result.final_candidate is None
    assert result.agreement_status == "qwen_unavailable"


def test_gross_type_mismatch_is_not_silently_accepted() -> None:
    qwen = _vision("Prepared Rehmannia Root", 0.9, material_type="animal")
    verification = _knowledge_verification(
        qwen,
        {
            "status": "matched",
            "profile": {
                "botanical_or_zoological_source": "Rehmannia glutinosa",
                "medicinal_part": "processed root",
            },
        },
    )
    assert verification["status"] == "gross_mismatch"
