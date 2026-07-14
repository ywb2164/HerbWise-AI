import pytest
from pydantic import ValidationError

from app.modules.resources.agent_schemas import (
    GeneratedResourcePayload,
    ResourceCitation,
    ResourceGenerationRequest,
)
from app.modules.resources.agent_service import deterministic_review
from app.modules.resources.rag_decision import RagDecisionService


def _context(resource_type: str = "knowledge_card") -> dict:
    return {
        "resource_request": {"resource_type": resource_type, "difficulty": "basic"},
        "targets": {
            "dimensions": ["appearance_identification"],
            "knowledge_points": ["黄芪性状"],
        },
    }


def _resource(**overrides: object) -> GeneratedResourcePayload:
    data: dict[str, object] = {
        "title": "黄芪学习卡",
        "resource_type": "knowledge_card",
        "learning_objectives": ["掌握黄芪性状"],
        "target_dimensions": ["appearance_identification"],
        "target_knowledge_points": ["黄芪性状"],
        "difficulty": "basic",
        "estimated_minutes": 10,
        "content_markdown": "黄芪的性状辨析学习提示。",
        "personalization_reason": "根据当前计划目标生成。",
    }
    data.update(overrides)
    return GeneratedResourcePayload.model_validate(data)


def test_non_professional_resources_do_not_require_rag() -> None:
    service = RagDecisionService()
    for resource_type in ("knowledge_card", "review_summary", "practice_guide"):
        decision = service.decide(
            resource_type=resource_type,
            requires_citation=False,
            knowledge_points=["黄芪性状"],
            additional_instruction=None,
        )
        assert not decision.requires_rag


def test_citation_and_professional_resources_require_rag() -> None:
    service = RagDecisionService()
    assert service.decide(
        resource_type="knowledge_card",
        requires_citation=True,
        knowledge_points=["黄芪性状"],
        additional_instruction=None,
    ).requires_rag
    assert service.decide(
        resource_type="professional_guide",
        requires_citation=False,
        knowledge_points=["黄芪性状"],
        additional_instruction=None,
    ).requires_rag


def test_deterministic_review_rejects_unknown_evidence_and_missing_required_citation() -> (
    None
):
    output = _resource(
        citations=[ResourceCitation(evidence_id="invented", citation="p.1")]
    )
    issues = deterministic_review(output, _context(), [], True)
    assert "invalid_evidence" in issues


def test_deterministic_review_rejects_pharmacopoeia_claim_without_evidence() -> None:
    output = _resource(content_markdown="根据《中国药典》黄芪性状辨析学习提示。")
    assert "fabricated_page" in deterministic_review(output, _context(), [], False)


def test_deterministic_review_accepts_current_evidence_citation() -> None:
    evidence = [{"evidence_id": "ev_1", "citation": "授权教材 p.1"}]
    output = _resource(
        citations=[ResourceCitation(evidence_id="ev_1", citation="授权教材 p.1")]
    )
    assert deterministic_review(output, _context(), evidence, True) == []


def test_job_request_requires_a_task_or_plan_item_and_whitelisted_type() -> None:
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(
            learner_id="stu_001", resource_type="knowledge_card", difficulty="basic"
        )
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(
            learner_id="stu_001",
            task_id="learn_001",
            resource_type="unregistered",
            difficulty="basic",
        )
