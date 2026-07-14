import pytest

from app.modules.learning_paths.plan_schemas import (
    LearningPlanItemProposal,
    LearningPlanProposal,
)
from app.modules.learning_paths.plan_service import (
    PlanValidationService,
    deterministic_fallback_plan,
)


def _context() -> dict:
    return {
        "daily_minutes": 30,
        "valid_dimension_codes": ["basic_knowledge", "character_identification"],
        "pending_tasks": [],
        "dimensions": [
            {"code": "basic_knowledge", "score": 45},
            {"code": "character_identification", "score": 70},
        ],
        "weak_points": [
            {
                "dimension_code": "basic_knowledge",
                "knowledge_point": "herb basics",
                "severity": "high",
            }
        ],
        "recent_accuracy": 0.5,
    }


def _proposal(**item_overrides: object) -> LearningPlanProposal:
    item = {
        "title": "Foundation practice",
        "reason": "Lowest dimension",
        "target_dimensions": ["basic_knowledge"],
        "target_knowledge_points": ["herb basics"],
        "task_type": "quiz",
        "difficulty": "basic",
        "estimated_minutes": 20,
        "resource_type": "comparison_card",
    }
    item.update(item_overrides)
    return LearningPlanProposal(
        stage="consolidation",
        summary="summary",
        goal="goal",
        daily_minutes=30,
        items=[LearningPlanItemProposal(**item)],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target_dimensions", ["invented_dimension"], "unknown dimensions"),
        ("difficulty", "impossible", "difficulty is invalid"),
        ("task_type", "invented_task", "task_type is invalid"),
    ],
)
async def test_plan_validation_rejects_invalid_model_values(
    field: str, value: object, message: str
) -> None:
    errors = await PlanValidationService().validate(
        None, "stu_001", _proposal(**{field: value}), _context()
    )
    assert any(message in error for error in errors)


@pytest.mark.asyncio
async def test_plan_validation_rejects_empty_and_over_budget_plans() -> None:
    empty = LearningPlanProposal(
        stage="stage", summary="summary", goal="goal", daily_minutes=30, items=[]
    )
    over_budget = _proposal(estimated_minutes=31)
    validator = PlanValidationService()
    assert "items must contain between 1 and 5 entries" in await validator.validate(
        None, "stu_001", empty, _context()
    )
    assert "total estimated minutes exceeds daily_minutes" in await validator.validate(
        None, "stu_001", over_budget, _context()
    )


def test_fallback_plan_targets_lowest_dimension_without_model_call() -> None:
    plan = deterministic_fallback_plan(_context())
    assert plan.items[0].target_dimensions == ["basic_knowledge"]
    assert plan.items[0].difficulty == "basic"
    assert plan.daily_minutes == 30
