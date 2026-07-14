"""Deterministic services for the personalised learning-plan agent.

The LLM is confined to proposing a schema-shaped plan.  This module owns all
database reads/writes, validation, duplicate prevention and task binding.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.exceptions import AppException, NotFoundException
from app.modules.learning_paths.models import (
    LearningPlan,
    LearningPlanItem,
    LearningQuestion,
    LearningTask,
    LearningTaskAnswer,
    LearningTaskAttempt,
    LearningTaskQuestion,
)
from app.modules.learning_paths.plan_schemas import (
    LearningPlanItemProposal,
    LearningPlanProposal,
)
from app.modules.learning_paths.task_service import create_task_for_learning_plan
from app.modules.profiles.models import LearnerDimension, LearnerWeakPoint
from app.modules.profiles.rules import DIMENSION_CODES
from app.modules.profiles.service import require_profile

PROMPT_VERSION = "learning-plan-v1"
VALID_TASK_TYPES = {"quiz", "comparison_practice", "review_practice"}
VALID_RESOURCE_TYPES = {"none", "comparison_card", "study_note", "guide", "lecture"}
VALID_DIFFICULTIES = {"basic", "intermediate", "advanced"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class PlanValidationError(AppException):
    status_code = 422
    code = 1422

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("Learning plan validation failed: " + "; ".join(self.errors))


def difficulty_for_accuracy(accuracy: float) -> str:
    if accuracy < 0.60:
        return "basic"
    if accuracy <= 0.85:
        return "intermediate"
    return "advanced"


async def load_learning_context(
    session: AsyncSession, learner_id: str, daily_minutes: int
) -> dict[str, Any]:
    """Load a bounded, model-safe summary; never return credentials or PII."""

    await require_profile(session, learner_id)
    dimensions = list(
        (
            await session.scalars(
                select(LearnerDimension)
                .where(LearnerDimension.learner_id == learner_id)
                .order_by(LearnerDimension.score)
            )
        ).all()
    )
    weak_points = list(
        (
            await session.scalars(
                select(LearnerWeakPoint).where(
                    LearnerWeakPoint.learner_id == learner_id,
                    LearnerWeakPoint.is_resolved.is_(False),
                )
            )
        ).all()
    )
    weak_points.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.id))
    attempts = list(
        (
            await session.execute(
                select(LearningTaskAttempt, LearningTask)
                .join(
                    LearningTask,
                    LearningTask.learning_task_id == LearningTaskAttempt.task_id,
                )
                .where(
                    LearningTaskAttempt.learner_id == learner_id,
                    LearningTaskAttempt.status == "completed",
                )
                .order_by(LearningTaskAttempt.submitted_at.desc())
                .limit(10)
            )
        )
        .tuples()
        .all()
    )
    errors = list(
        (
            await session.execute(
                select(LearningTaskAnswer, LearningQuestion)
                .join(
                    LearningTaskAttempt,
                    LearningTaskAttempt.attempt_id == LearningTaskAnswer.attempt_id,
                )
                .join(
                    LearningTaskQuestion,
                    and_(
                        LearningTaskQuestion.task_id == LearningTaskAttempt.task_id,
                        LearningTaskQuestion.question_id
                        == LearningTaskAnswer.question_id,
                    ),
                )
                .join(
                    LearningQuestion,
                    LearningQuestion.id == LearningTaskAnswer.question_id,
                )
                .where(
                    LearningTaskAttempt.learner_id == learner_id,
                    LearningTaskAnswer.is_correct.is_(False),
                )
                .order_by(LearningTaskAnswer.created_at.desc())
                .limit(20)
            )
        )
        .tuples()
        .all()
    )
    pending = list(
        (
            await session.scalars(
                select(LearningTask)
                .where(
                    LearningTask.learner_id == learner_id,
                    LearningTask.status.in_(("pending", "in_progress")),
                )
                .order_by(LearningTask.created_at.desc())
                .limit(20)
            )
        ).all()
    )
    completed_count = (
        await session.scalar(
            select(func.count())
            .select_from(LearningTask)
            .where(
                LearningTask.learner_id == learner_id,
                LearningTask.status == "completed",
            )
        )
    ) or 0
    accuracy = await session.scalar(
        select(func.avg(LearningTaskAttempt.accuracy)).where(
            LearningTaskAttempt.learner_id == learner_id,
            LearningTaskAttempt.status == "completed",
            LearningTaskAttempt.accuracy.is_not(None),
        )
    )
    return {
        "learner_id": learner_id,
        "dimensions": [
            {"code": item.dimension_code or item.dimension_key, "score": item.score}
            for item in dimensions
        ],
        "valid_dimension_codes": list(DIMENSION_CODES),
        "weak_points": [
            {
                "dimension_code": item.dimension_code,
                "knowledge_point": item.knowledge_point,
                "severity": item.severity,
            }
            for item in weak_points[:20]
        ],
        "recent_tasks": [
            {
                "task_type": task.task_type,
                "difficulty": task.difficulty,
                "target_dimensions": task.target_dimension_codes_json or [],
                "target_knowledge_points": task.target_knowledge_points_json or [],
                "accuracy": attempt.accuracy,
            }
            for attempt, task in attempts
        ],
        "recent_errors": [
            {
                "dimension_code": question.dimension_code,
                "knowledge_point": question.knowledge_point,
            }
            for _, question in errors
        ],
        "pending_tasks": [
            {
                "task_id": task.learning_task_id,
                "task_type": task.task_type,
                "difficulty": task.difficulty,
                "target_dimensions": task.target_dimension_codes_json or [],
                "target_knowledge_points": task.target_knowledge_points_json or [],
            }
            for task in pending
        ],
        "completed_task_count": int(completed_count),
        "recent_accuracy": round(float(accuracy or 0), 4),
        "daily_minutes": daily_minutes,
    }


class PlanValidationService:
    async def validate(
        self,
        session: AsyncSession,
        learner_id: str,
        proposal: LearningPlanProposal,
        context: dict[str, Any],
    ) -> list[str]:
        del (
            session
        )  # All data needed for deterministic validation is in the bounded context.
        errors: list[str] = []
        if proposal.daily_minutes != context["daily_minutes"]:
            errors.append("daily_minutes must match the requested value")
        if not 1 <= len(proposal.items) <= 5:
            errors.append("items must contain between 1 and 5 entries")
        total_minutes = sum(item.estimated_minutes for item in proposal.items)
        if total_minutes > context["daily_minutes"]:
            errors.append("total estimated minutes exceeds daily_minutes")
        if (
            not proposal.stage.strip()
            or not proposal.summary.strip()
            or not proposal.goal.strip()
        ):
            errors.append("stage, summary and goal must not be empty")
        pending_points = {
            point
            for task in context["pending_tasks"]
            for point in task["target_knowledge_points"]
        }
        seen_points: set[str] = set()
        for index, item in enumerate(proposal.items, start=1):
            prefix = f"item {index}"
            if not item.title.strip() or not item.reason.strip():
                errors.append(f"{prefix} title and reason must not be empty")
            if item.task_type not in VALID_TASK_TYPES:
                errors.append(f"{prefix} task_type is invalid")
            if item.resource_type not in VALID_RESOURCE_TYPES:
                errors.append(f"{prefix} resource_type is invalid")
            if item.difficulty not in VALID_DIFFICULTIES:
                errors.append(f"{prefix} difficulty is invalid")
            if not 5 <= item.estimated_minutes <= 60:
                errors.append(f"{prefix} estimated_minutes must be between 5 and 60")
            if not item.target_dimensions:
                errors.append(f"{prefix} requires a target dimension")
            invalid = set(item.target_dimensions) - set(
                context["valid_dimension_codes"]
            )
            if invalid:
                errors.append(f"{prefix} contains unknown dimensions")
            points = {
                point.strip() for point in item.target_knowledge_points if point.strip()
            }
            if not points:
                errors.append(f"{prefix} requires a target knowledge point")
            if points & seen_points:
                errors.append(f"{prefix} duplicates a plan knowledge point")
            if points & pending_points:
                errors.append(f"{prefix} duplicates a pending task knowledge point")
            seen_points.update(points)
        return errors


def deterministic_fallback_plan(context: dict[str, Any]) -> LearningPlanProposal:
    scores = {item["code"]: item["score"] for item in context["dimensions"]}
    target = min(context["valid_dimension_codes"], key=lambda code: scores.get(code, 0))
    weak_point = next(
        (item for item in context["weak_points"] if item["dimension_code"] == target),
        None,
    )
    dimension_label = {
        "basic_knowledge": "基础知识",
        "character_identification": "性状辨识",
        "similar_medicine": "相似药材辨析",
        "pharmacopoeia_rules": "药典规范",
        "clinical_quality_control": "质量控制",
        "practical_review": "实践复核",
    }.get(target, "当前学习重点")
    knowledge_point = (
        weak_point["knowledge_point"] if weak_point else f"{dimension_label}基础"
    )
    minutes = min(max(5, context["daily_minutes"]), 30)
    return LearningPlanProposal(
        stage="consolidation",
        summary=f"当前{dimension_label}维度相对薄弱，建议优先完成本次练习。",
        goal=f"通过针对性练习巩固{dimension_label}。",
        daily_minutes=context["daily_minutes"],
        items=[
            LearningPlanItemProposal(
                title=f"{dimension_label}巩固练习",
                reason=f"当前{dimension_label}维度相对薄弱，建议优先巩固。",
                target_dimensions=[target],
                target_knowledge_points=[knowledge_point],
                task_type="quiz",
                difficulty=difficulty_for_accuracy(context["recent_accuracy"]),
                estimated_minutes=minutes,
                resource_type="comparison_card",
            )
        ],
    )


async def bind_learning_tasks(
    session: AsyncSession, learner_id: str, proposal: LearningPlanProposal
) -> list[str | None]:
    linked: list[str | None] = []
    pending = list(
        (
            await session.scalars(
                select(LearningTask).where(
                    LearningTask.learner_id == learner_id,
                    LearningTask.status.in_(("pending", "in_progress")),
                )
            )
        ).all()
    )
    for item in proposal.items:
        dimensions, points = (
            set(item.target_dimensions),
            set(item.target_knowledge_points),
        )
        existing = next(
            (
                task
                for task in pending
                if dimensions.intersection(task.target_dimension_codes_json or [])
                and points.intersection(task.target_knowledge_points_json or [])
            ),
            None,
        )
        if existing is None:
            created = await create_task_for_learning_plan(
                session,
                learner_id,
                dimension=item.target_dimensions[0],
                difficulty=item.difficulty,
                task_type=item.task_type,
                reason=item.reason,
                knowledge_point=item.target_knowledge_points[0],
            )
            if created is not None:
                pending.append(created)
                existing = created
        linked.append(existing.learning_task_id if existing is not None else None)
    return linked


async def persist_plan(
    session: AsyncSession,
    learner_id: str,
    proposal: LearningPlanProposal,
    context: dict[str, Any],
    linked_task_ids: list[str | None],
    *,
    provider: str | None,
    model_name: str | None,
    data_source: str,
    fallback_used: bool,
) -> LearningPlan:
    active = list(
        (
            await session.scalars(
                select(LearningPlan).where(
                    LearningPlan.learner_id == learner_id,
                    LearningPlan.status == "active",
                )
            )
        ).all()
    )
    for active_plan in active:
        active_plan.status = "completed"
    plan = LearningPlan(
        plan_id=new_id("plan"),
        learner_id=learner_id,
        status="active",
        stage=proposal.stage,
        summary=proposal.summary,
        goal=proposal.goal,
        daily_minutes=proposal.daily_minutes,
        total_estimated_minutes=sum(item.estimated_minutes for item in proposal.items),
        profile_snapshot_json=json_safe({"dimensions": context["dimensions"]}),
        weak_points_snapshot_json=json_safe(context["weak_points"]),
        recent_performance_snapshot_json=json_safe(
            {
                "recent_tasks": context["recent_tasks"],
                "recent_errors": context["recent_errors"],
                "recent_accuracy": context["recent_accuracy"],
                "completed_task_count": context["completed_task_count"],
            }
        ),
        provider=provider,
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        data_source=data_source,
        fallback_used=fallback_used,
    )
    session.add(plan)
    await session.flush()
    for index, (plan_item, task_id) in enumerate(
        zip(proposal.items, linked_task_ids, strict=True), start=1
    ):
        session.add(
            LearningPlanItem(
                item_id=new_id("plan_item"),
                plan_id=plan.plan_id,
                order_index=index,
                title=plan_item.title,
                reason=plan_item.reason,
                target_dimensions_json=plan_item.target_dimensions,
                target_knowledge_points_json=plan_item.target_knowledge_points,
                task_type=plan_item.task_type,
                difficulty=plan_item.difficulty,
                estimated_minutes=plan_item.estimated_minutes,
                resource_type=plan_item.resource_type,
                status="pending",
                linked_task_id=task_id,
            )
        )
    await session.commit()
    await session.refresh(plan)
    return plan


def plan_data(plan: LearningPlan, items: list[LearningPlanItem]) -> dict[str, Any]:
    return {
        "plan_id": plan.plan_id,
        "status": plan.status,
        "stage": plan.stage,
        "summary": plan.summary,
        "goal": plan.goal,
        "daily_minutes": plan.daily_minutes,
        "total_estimated_minutes": plan.total_estimated_minutes,
        "fallback_used": plan.fallback_used,
        "items": [
            {
                "item_id": item.item_id,
                "order_index": item.order_index,
                "title": item.title,
                "reason": item.reason,
                "target_dimensions": item.target_dimensions_json,
                "target_knowledge_points": item.target_knowledge_points_json,
                "task_type": item.task_type,
                "difficulty": item.difficulty,
                "estimated_minutes": item.estimated_minutes,
                "resource_type": item.resource_type,
                "status": item.status,
                "linked_task_id": item.linked_task_id,
                "linked_resource_id": item.linked_resource_id,
            }
            for item in sorted(items, key=lambda value: value.order_index)
        ],
    }


async def get_plan(
    session: AsyncSession, plan_id: str, learner_id: str
) -> dict[str, Any]:
    plan = await session.scalar(
        select(LearningPlan).where(
            LearningPlan.plan_id == plan_id, LearningPlan.learner_id == learner_id
        )
    )
    if plan is None:
        raise NotFoundException("Learning plan not found")
    items = list(
        (
            await session.scalars(
                select(LearningPlanItem).where(LearningPlanItem.plan_id == plan_id)
            )
        ).all()
    )
    return plan_data(plan, items)


async def list_plans(session: AsyncSession, learner_id: str) -> list[dict[str, Any]]:
    plans = list(
        (
            await session.scalars(
                select(LearningPlan)
                .where(LearningPlan.learner_id == learner_id)
                .order_by(LearningPlan.created_at.desc())
            )
        ).all()
    )
    return [
        plan_data(
            plan,
            list(
                (
                    await session.scalars(
                        select(LearningPlanItem).where(
                            LearningPlanItem.plan_id == plan.plan_id
                        )
                    )
                ).all()
            ),
        )
        for plan in plans
    ]


async def current_plan(session: AsyncSession, learner_id: str) -> dict[str, Any] | None:
    plan = await session.scalar(
        select(LearningPlan)
        .where(LearningPlan.learner_id == learner_id, LearningPlan.status == "active")
        .order_by(LearningPlan.updated_at.desc())
    )
    return await get_plan(session, plan.plan_id, learner_id) if plan else None


async def transition_plan(
    session: AsyncSession, plan_id: str, learner_id: str, status: str
) -> dict[str, Any]:
    plan = await session.scalar(
        select(LearningPlan).where(
            LearningPlan.plan_id == plan_id, LearningPlan.learner_id == learner_id
        )
    )
    if plan is None:
        raise NotFoundException("Learning plan not found")
    if status == "active":
        for other in list(
            (
                await session.scalars(
                    select(LearningPlan).where(
                        LearningPlan.learner_id == learner_id,
                        LearningPlan.status == "active",
                    )
                )
            ).all()
        ):
            if other.plan_id != plan_id:
                other.status = "completed"
    plan.status = status
    await session.commit()
    return await get_plan(session, plan_id, learner_id)
