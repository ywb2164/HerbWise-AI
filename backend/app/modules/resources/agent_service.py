"""Deterministic boundary for the personalised learning-resource agent."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.config import get_settings
from app.core.exceptions import AppException, NotFoundException
from app.integrations.contracts import GeneratedResource, ModelCallContext
from app.integrations.factory import get_llm_provider
from app.integrations.runtime_model import runtime_model_registry
from app.modules.knowledge.models import MedicineFeature, MedicineItem
from app.modules.learning_paths.models import (
    LearningPlan,
    LearningPlanItem,
    LearningTask,
)
from app.modules.learning_paths.plan_service import load_learning_context
from app.modules.profiles.service import profile_data, require_profile
from app.modules.resources.agent_schemas import (
    GeneratedResourcePayload,
    ModelResourceReview,
    ResourceGenerationRequest,
)
from app.modules.resources.business_models import (
    ResourceGenerationJob,
    ResourceOutput,
    ResourceReview,
)

PROMPT_VERSION = "learning-resource-agent-v1"
SEVERE_REVIEW_ISSUES = frozenset(
    {
        "invalid_evidence",
        "cross_task_citation",
        "fabricated_page",
        "citation_required_but_missing",
        "prompt_leak",
        "credential_leak",
    }
)


def job_data(job: ResourceGenerationJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "learner_id": job.learner_id,
        "plan_id": job.plan_id,
        "learning_plan_item_id": job.plan_item_id,
        "task_id": job.task_id,
        "resource_type": job.resource_type,
        "difficulty": job.difficulty,
        "status": job.status,
        "requires_rag": job.requires_rag,
        "rag_reason_codes": job.rag_reason_json or [],
        "retrieval_id": job.retrieval_id,
        "resource_id": job.resource_id,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
    }


async def require_job(
    session: AsyncSession, job_id: str, learner_id: str | None = None
) -> ResourceGenerationJob:
    job = await session.scalar(
        select(ResourceGenerationJob).where(ResourceGenerationJob.job_id == job_id)
    )
    if job is None or (learner_id is not None and job.learner_id != learner_id):
        raise NotFoundException("Resource generation job not found")
    return job


async def create_job(
    session: AsyncSession, payload: ResourceGenerationRequest
) -> ResourceGenerationJob:
    profile = await require_profile(session, payload.learner_id)
    del profile
    job = ResourceGenerationJob(
        job_id=new_id("resjob"),
        learner_id=payload.learner_id,
        plan_item_id=payload.learning_plan_item_id,
        task_id=payload.task_id,
        resource_type=payload.resource_type,
        difficulty=payload.difficulty,
        additional_instruction=payload.additional_instruction,
        status="pending",
    )
    session.add(job)
    await session.flush()
    return job


async def _load_context(
    session: AsyncSession, job: ResourceGenerationJob, requires_citation: bool
) -> dict[str, Any]:
    profile = await require_profile(session, job.learner_id)
    plan_item = None
    plan = None
    if job.plan_item_id:
        plan_item = await session.scalar(
            select(LearningPlanItem).where(LearningPlanItem.item_id == job.plan_item_id)
        )
        if plan_item is None:
            raise NotFoundException("Learning plan item not found")
        plan = await session.scalar(
            select(LearningPlan).where(
                LearningPlan.plan_id == plan_item.plan_id,
                LearningPlan.learner_id == job.learner_id,
            )
        )
        if plan is None:
            raise NotFoundException("Learning plan item not found")
        job.plan_id = plan.plan_id
    task = None
    if job.task_id:
        task = await session.scalar(
            select(LearningTask).where(
                LearningTask.learning_task_id == job.task_id,
                LearningTask.learner_id == job.learner_id,
            )
        )
        if task is None:
            raise NotFoundException("Learning task not found")
    if plan_item and task and plan_item.linked_task_id != task.learning_task_id:
        raise AppException("Learning plan item and task are not linked")
    if plan_item and not job.task_id:
        job.task_id = plan_item.linked_task_id
        if job.task_id:
            task = await session.scalar(
                select(LearningTask).where(
                    LearningTask.learning_task_id == job.task_id,
                    LearningTask.learner_id == job.learner_id,
                )
            )
    learning = await load_learning_context(session, job.learner_id, 30)
    targets = (
        list(plan_item.target_knowledge_points_json or [])
        if plan_item
        else list(task.target_knowledge_points_json or [])
        if task
        else []
    )
    dimensions = (
        list(plan_item.target_dimensions_json or [])
        if plan_item
        else list(task.target_dimension_codes_json or [])
        if task
        else []
    )
    return {
        "learner": {
            "learner_id": job.learner_id,
            "dimensions": learning["dimensions"],
            "weak_points": learning["weak_points"],
            "recent_accuracy": learning["recent_accuracy"],
        },
        "profile_snapshot": profile_data(profile),
        "learning_plan": (
            {"plan_id": plan.plan_id, "goal": plan.goal, "stage": plan.stage}
            if plan
            else None
        ),
        "plan_item": (
            {
                "item_id": plan_item.item_id,
                "title": plan_item.title,
                "reason": plan_item.reason,
                "target_dimensions": dimensions,
                "target_knowledge_points": targets,
                "difficulty": plan_item.difficulty,
            }
            if plan_item
            else None
        ),
        "task": (
            {
                "task_id": task.learning_task_id,
                "task_type": task.task_type,
                "target_dimensions": task.target_dimension_codes_json or [],
                "question_topics": task.target_knowledge_points_json or [],
            }
            if task
            else None
        ),
        "targets": {"dimensions": dimensions, "knowledge_points": targets},
        "resource_request": {
            "resource_type": job.resource_type,
            "difficulty": job.difficulty,
            "requires_citation": requires_citation,
            "additional_instruction": job.additional_instruction,
        },
    }


async def _load_structured_knowledge(
    session: AsyncSession, context: dict[str, Any]
) -> dict[str, Any]:
    targets = context["targets"]["knowledge_points"]
    medicines = (
        list(
            (
                await session.scalars(
                    select(MedicineItem).where(
                        MedicineItem.standard_name_zh.in_(targets)
                    )
                )
            ).all()
        )
        if targets
        else []
    )
    features = (
        list(
            (
                await session.scalars(
                    select(MedicineFeature).where(
                        MedicineFeature.medicine_id.in_([item.id for item in medicines])
                    )
                )
            ).all()
        )
        if medicines
        else []
    )
    return {
        "medicines": [
            {
                "id": item.id,
                "name": item.standard_name_zh,
                "source": item.source,
                "description": item.description,
            }
            for item in medicines
        ],
        "features": [
            {
                "medicine_id": item.medicine_id,
                "name": item.feature_name,
                "type": item.feature_type,
                "value": item.feature_value,
            }
            for item in features[:20]
        ],
    }


def _fallback_resource(
    context: dict[str, Any], *, reason: str | None = None
) -> GeneratedResourcePayload:
    targets = context["targets"]
    title_target = "、".join(targets["knowledge_points"][:2]) or "目标知识点"
    resource_type = context["resource_request"]["resource_type"]
    description = (
        "；".join(
            f"{item['name']}：{item['value']}"
            for item in context.get("knowledge", {}).get("features", [])[:6]
        )
        or "请围绕任务目标，结合已掌握和待巩固的特征进行复习。"
    )
    return GeneratedResourcePayload(
        title=f"{title_target}{'对比' if 'comparison' in resource_type else '学习'}卡",
        resource_type=resource_type,
        learning_objectives=[f"掌握{title_target}的核心辨析要点"],
        target_dimensions=targets["dimensions"] or ["basic_knowledge"],
        target_knowledge_points=targets["knowledge_points"] or [title_target],
        difficulty=context["resource_request"]["difficulty"],
        estimated_minutes=10,
        content_markdown=f"# {title_target}\n\n{description}\n\n## 学习建议\n依据当前计划目标逐项复习，并在任务中核对易混淆特征。",
        key_points=[description],
        questions=[],
        citations=[],
        personalization_reason=(
            reason or "该资源根据当前学习计划、薄弱知识点和近期完成情况生成。"
        ),
    )


def _can_use_text_model(learner_id: str) -> bool:
    return (
        runtime_model_registry.get_for_learner(learner_id, "text") is not None
        or get_settings().llm_mode == "real"
    )


async def _generate_with_text_model(
    job: ResourceGenerationJob,
    context: dict[str, Any],
    evidence: list[dict[str, Any]],
    rewrite_instructions: list[str] | None = None,
) -> GeneratedResourcePayload:
    result = await get_llm_provider(learner_id=job.learner_id).complete_structured(
        [
            {
                "role": "system",
                "content": (
                    "你是中药学个性化学习资源生成助手。只使用给定结构化知识和证据，"
                    "不得伪造来源、页码或药典结论；不得提供临床诊断或处方；只输出 JSON。"
                ),
            },
            {
                "role": "user",
                "content": str(
                    {
                        "context": context,
                        "evidence": evidence,
                        "rewrite_instructions": rewrite_instructions or [],
                    }
                ),
            },
        ],
        GeneratedResourcePayload,
        ModelCallContext(
            learner_id=job.learner_id,
            task_id=job.task_id,
            agent_code="learning_resource_generation",
            prompt_template_code="learning_resource_generation",
            prompt_version=PROMPT_VERSION,
        ),
    )
    return GeneratedResourcePayload.model_validate(result)


def deterministic_review(
    output: GeneratedResourcePayload,
    context: dict[str, Any],
    evidence: list[dict[str, Any]],
    requires_rag: bool,
) -> list[str]:
    issues: list[str] = []
    request = context["resource_request"]
    targets = context["targets"]
    if output.resource_type != request["resource_type"]:
        issues.append("resource_type_mismatch")
    if output.difficulty != request["difficulty"]:
        issues.append("difficulty_mismatch")
    if not set(output.target_dimensions).issubset(set(targets["dimensions"])):
        issues.append("invalid_target_dimension")
    if not output.target_knowledge_points:
        issues.append("missing_knowledge_point")
    if len(output.content_markdown) > 20000:
        issues.append("content_too_long")
    for question in output.questions:
        if question.options and question.answer not in question.options:
            issues.append("invalid_question_answer")
    valid_evidence_ids = {str(item["evidence_id"]) for item in evidence}
    for citation in output.citations:
        if citation.evidence_id not in valid_evidence_ids:
            issues.append("invalid_evidence")
    text = output.content_markdown.casefold()
    if not evidence and ("中国药典" in text or "pharmacopoeia" in text):
        issues.append("fabricated_page")
    if requires_rag and not output.citations:
        issues.append("citation_required_but_missing")
    if any(token in text for token in ("system prompt", "<system>", "提示词")):
        issues.append("prompt_leak")
    if any(token in text for token in ("api_key", "authorization: bearer", "sk-")):
        issues.append("credential_leak")
    return sorted(set(issues))


async def _model_review(
    job: ResourceGenerationJob,
    output: GeneratedResourcePayload,
    context: dict[str, Any],
    evidence: list[dict[str, Any]],
    deterministic_issues: list[str],
) -> ModelResourceReview:
    if not _can_use_text_model(job.learner_id):
        return ModelResourceReview(decision="pass", score=1, issues=[])
    provider = get_llm_provider(learner_id=job.learner_id)
    reviewed = await provider.review_resource(
        [
            GeneratedResource(
                title=output.title,
                content=output.content_markdown,
                resource_type=output.resource_type,
                content_json=output.model_dump(mode="json"),
            )
        ],
        ModelCallContext(
            learner_id=job.learner_id,
            task_id=job.task_id,
            agent_code="learning_resource_review",
            prompt_template_code="learning_resource_review",
            prompt_version=PROMPT_VERSION,
        ),
    )
    status = reviewed.status.casefold()
    decision: Literal["pass", "rewrite", "reject"] = (
        "pass"
        if status in {"pass", "approved"}
        else "rewrite"
        if status in {"needs_revision", "rewrite"}
        else "reject"
    )
    return ModelResourceReview(
        decision=decision,
        score=max(0, min(1, 1 - reviewed.hallucination_risk_score / 100)),
        issues=reviewed.issues,
        rewrite_required=decision == "rewrite",
        rewrite_instructions=reviewed.suggestions,
    )


async def _persist_resource(
    session: AsyncSession,
    job: ResourceGenerationJob,
    context: dict[str, Any],
    output: GeneratedResourcePayload,
    evidence: list[dict[str, Any]],
    review: ModelResourceReview,
    *,
    fallback_used: bool,
    rewrite_count: int,
    resource_status: str = "approved",
) -> ResourceOutput:
    runtime = runtime_model_registry.get_for_learner(job.learner_id, "text")
    item = ResourceOutput(
        resource_id=new_id("res"),
        learner_id=job.learner_id,
        plan_id=job.plan_id,
        plan_item_id=job.plan_item_id,
        task_id=job.task_id,
        resource_type=output.resource_type,
        title=output.title,
        content_markdown=output.content_markdown,
        content_json=json_safe(
            {
                "key_points": output.key_points,
                "questions": [item.model_dump() for item in output.questions],
                "safety_notice": output.safety_notice,
            }
        ),
        learning_objectives_json=output.learning_objectives,
        target_dimensions_json=output.target_dimensions,
        target_knowledge_points_json=output.target_knowledge_points,
        difficulty=output.difficulty,
        estimated_minutes=output.estimated_minutes,
        personalization_reason=output.personalization_reason,
        status=resource_status,
        provider=(
            f"{runtime.protocol}_compatible"
            if runtime
            else "deterministic"
            if fallback_used
            else "openai_compatible"
        ),
        model_name=runtime.model_name
        if runtime
        else None
        if fallback_used
        else get_settings().text_model,
        prompt_version=PROMPT_VERSION,
        profile_snapshot_json=json_safe(context["learner"]),
        task_snapshot_json=json_safe(context.get("task")),
        knowledge_snapshot_json=json_safe(context.get("knowledge", {})),
        evidence_snapshot_json=json_safe({"items": evidence}),
        generation_metadata_json={
            "job_id": job.job_id,
            "requires_rag": job.requires_rag,
        },
        retrieval_id=job.retrieval_id,
        evidence_ids_json=[item["evidence_id"] for item in evidence],
        citations_json=[item.model_dump() for item in output.citations],
        citation_count=len(output.citations),
        review_status=review.decision,
        review_score=review.score,
        rewrite_count=rewrite_count,
        version=rewrite_count + 1,
        data_source="deterministic_fallback"
        if fallback_used
        else "ragflow"
        if evidence
        else "database",
        fallback_used=fallback_used,
    )
    session.add(item)
    await session.flush()
    session.add(
        ResourceReview(
            review_id=new_id("review"),
            resource_id=item.resource_id,
            status="pass" if resource_status == "approved" else "reject",
            pharmacopoeia_consistency_score=review.score * 100,
            terminology_accuracy_score=review.score * 100,
            source_completeness_score=100 if evidence or not job.requires_rag else 0,
            answer_accuracy_score=100,
            hallucination_risk_score=(1 - review.score) * 100,
            medical_risk_score=0,
            issues_json=review.issues,
            suggestions_json=review.rewrite_instructions,
            evidence_json={"items": evidence},
            provider=item.provider,
            model_name=item.model_name,
            prompt_version=PROMPT_VERSION,
            reviewed_at=datetime.now(UTC),
            retrieval_id=job.retrieval_id,
            citation_validity_score=100,
            evidence_coverage_score=100 if evidence else 0,
            citation_check_json={"valid": True, "issues": []},
            evidence_ids_json=item.evidence_ids_json,
            data_source=item.data_source,
        )
    )
    return item


async def run_job_workflow(
    session: AsyncSession,
    job: ResourceGenerationJob,
    *,
    requires_citation: bool = False,
) -> None:
    """Run the LangGraph workflow in-process while preserving its persisted job state."""

    from app.workflows.resource_generation_graph import run_resource_generation

    await run_resource_generation(session, job, requires_citation=requires_citation)


async def retry_resource(
    session: AsyncSession, resource: ResourceOutput
) -> ResourceGenerationJob:
    if resource.status not in {"rejected", "failed"}:
        raise AppException("Only rejected or failed resources can be retried")
    job = ResourceGenerationJob(
        job_id=new_id("resjob"),
        learner_id=resource.learner_id,
        plan_id=resource.plan_id,
        plan_item_id=resource.plan_item_id,
        task_id=resource.task_id,
        resource_type=resource.resource_type,
        difficulty=resource.difficulty,
        status="pending",
    )
    session.add(job)
    await session.flush()
    return job
