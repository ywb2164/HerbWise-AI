from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.exceptions import NotFoundException
from app.core.config import get_settings
from app.integrations.contracts import (
    GeneratedResource,
    KnowledgeEvidence,
    ModelCallContext,
)
from app.integrations.factory import get_llm_provider, get_rag_provider
from app.integrations.runtime_model import runtime_model_registry
from app.modules.knowledge.service import find_medicine_by_name, require_medicine
from app.modules.profiles.service import profile_data, require_profile
from app.modules.resources.business_models import (
    PromptTemplate,
    QuizQuestion,
    ResourceOutput,
    ResourceReview,
)
from app.modules.resources.business_schemas import GenerateResourceRequest
from app.modules.resources.citations import (
    resolve_citations,
    validate_resource_citations,
)
from app.modules.recognition.models import ModelCallRecord
from app.modules.system.models import ModelConfig


def resource_data(item: ResourceOutput) -> dict:
    return {
        "resource_id": item.resource_id,
        "learner_id": item.learner_id,
        "task_id": item.task_id,
        "medicine_id": item.medicine_id,
        "resource_type": item.resource_type,
        "title": item.title,
        "content_markdown": item.content_markdown,
        "content_json": item.content_json or {},
        "difficulty": item.difficulty,
        "status": item.status,
        "provider": item.provider,
        "model_name": item.model_name,
        "prompt_version": item.prompt_version,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def require_resource(session: AsyncSession, resource_id: str) -> ResourceOutput:
    item = await session.scalar(
        select(ResourceOutput).where(ResourceOutput.resource_id == resource_id)
    )
    if item is None:
        raise NotFoundException("Resource not found")
    return item


async def generate_resource(
    session: AsyncSession,
    payload: GenerateResourceRequest,
    parent_resource_id: str | None = None,
) -> ResourceOutput:
    profile = await require_profile(session, payload.learner_id)
    citations = (
        await resolve_citations(session, payload.retrieval_id, payload.evidence_ids)
        if payload.retrieval_id
        else []
    )
    medicine_match = await find_medicine_by_name(session, payload.medicine_name)
    medicine = await require_medicine(session, medicine_match["id"])
    evidence = [
        item.model_dump()
        for item in await get_rag_provider().retrieve(medicine.standard_name_zh)
    ]
    settings = get_settings()
    context = ModelCallContext(
        task_id=payload.task_id,
        learner_id=payload.learner_id,
        agent_code="resource_generation",
        prompt_template_code="resource_generation",
    )
    model_config = None
    runtime_config = runtime_model_registry.get_for_learner(payload.learner_id, "text")
    if runtime_config is None and settings.llm_mode == "real":
        model_config = await session.scalar(
            select(ModelConfig)
            .where(
                ModelConfig.is_active.is_(True),
                ModelConfig.provider != "mock",
                ModelConfig.model_type.in_(("generation", "text")),
            )
            .order_by(ModelConfig.id)
        )
    generated = await get_llm_provider(
        model_config, payload.learner_id
    ).generate_resource(
        [KnowledgeEvidence.model_validate(item) for item in evidence], context
    )
    template = await session.scalar(
        select(PromptTemplate)
        .where(
            PromptTemplate.task_type == payload.resource_type,
            PromptTemplate.is_active.is_(True),
        )
        .order_by(PromptTemplate.id)
    )
    first = generated[0]
    resource_id = new_id("res")
    mode = (
        "real" if runtime_config is not None or settings.llm_mode == "real" else "mock"
    )
    content = (
        f"# {first.title}\n\n{first.content}\n\nMedicine: {medicine.standard_name_zh}"
    )
    item = ResourceOutput(
        resource_id=resource_id,
        learner_id=payload.learner_id,
        task_id=payload.task_id,
        medicine_id=medicine.id,
        resource_type=payload.resource_type,
        title=first.title,
        content_markdown=content,
        content_json={
            "mode": mode,
            "parent_resource_id": parent_resource_id,
            **(first.content_json or {}),
        },
        difficulty=payload.difficulty,
        status="generated",
        provider=(
            f"{runtime_config.protocol}_compatible"
            if runtime_config
            else model_config.provider
            if model_config
            else "openai_compatible"
        )
        if mode == "real"
        else "mock",
        model_name=(
            runtime_config.model_name
            if runtime_config
            else model_config.model_name
            if model_config
            else settings.generation_model
        )
        if mode == "real"
        else "mock-llm",
        prompt_template_id=template.id if template else None,
        prompt_version=template.version if template else "v1",
        profile_snapshot_json=json_safe(profile_data(profile)),
        evidence_snapshot_json=json_safe({"items": evidence, "data_source": "mock"}),
        generation_metadata_json={
            "mode": mode,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        retrieval_id=payload.retrieval_id,
        evidence_ids_json=payload.evidence_ids,
        citations_json=citations,
        data_source="ragflow" if payload.retrieval_id else "mock",
    )
    session.add(item)
    session.add(
        ModelCallRecord(
            call_id=new_id("mcall"),
            task_id=payload.task_id,
            learner_id=payload.learner_id,
            agent_code="resource_generation",
            prompt_template_code="resource_generation",
            provider=item.provider,
            model_name=item.model_name,
            call_type="resource_generation",
            success=True,
        )
    )
    if payload.resource_type == "quiz":
        session.add(
            QuizQuestion(
                resource_id=resource_id,
                question_type="single_choice",
                stem=f"Which medicine is this resource about: {medicine.standard_name_zh}?",
                options_json=[
                    {"key": "A", "text": medicine.standard_name_zh},
                    {"key": "B", "text": "demo distractor"},
                ],
                correct_answer_json={"value": "A"},
                explanation="demo_seed_data: answer derived from the requested medicine",
                difficulty=payload.difficulty,
                dimension_code="basic_knowledge",
                knowledge_point=medicine.standard_name_zh,
                sort_order=1,
            )
        )
    await session.commit()
    await session.refresh(item)
    return item


async def list_resources(
    session: AsyncSession, page: int, page_size: int, learner_id: str | None
) -> dict:
    filters = [ResourceOutput.learner_id == learner_id] if learner_id else []
    total = (
        await session.scalar(
            select(func.count()).select_from(ResourceOutput).where(*filters)
        )
        or 0
    )
    records = list(
        (
            await session.scalars(
                select(ResourceOutput)
                .where(*filters)
                .order_by(ResourceOutput.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return {
        "items": [resource_data(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


async def archive_resource(session: AsyncSession, resource_id: str) -> ResourceOutput:
    item = await require_resource(session, resource_id)
    item.status = "archived"
    await session.commit()
    await session.refresh(item)
    return item


async def review_resource(
    session: AsyncSession,
    resource_id: str,
    manual_status: str | None = None,
    suggestions: list[str] | None = None,
) -> ResourceReview:
    resource = await require_resource(session, resource_id)
    citation_check = await validate_resource_citations(
        session,
        resource.retrieval_id,
        resource.evidence_ids_json,
        resource.content_markdown,
    )
    issues: list[str] = []
    if not resource.content_markdown.strip():
        issues.append("empty_content")
    if not citation_check["valid"]:
        issues.extend(citation_check["issues"])
    if not resource.evidence_snapshot_json:
        issues.append("missing_evidence")
    if resource.medicine_id is None:
        issues.append("missing_medicine")
    if len(resource.content_markdown) < 20 or len(resource.content_markdown) > 20000:
        issues.append("abnormal_length")
    if resource.medicine_id is not None:
        medicine = await require_medicine(session, resource.medicine_id)
        names = [medicine.standard_name_zh, medicine.standard_name_en]
        if not any(
            name and name.casefold() in resource.content_markdown.casefold()
            for name in names
        ):
            issues.append("medicine_mismatch")
    if resource.resource_type == "quiz":
        questions = list(
            (
                await session.scalars(
                    select(QuizQuestion).where(
                        QuizQuestion.resource_id == resource.resource_id
                    )
                )
            ).all()
        )
        if not questions:
            issues.append("missing_quiz_questions")
        elif any(
            not question.correct_answer_json or not question.explanation
            for question in questions
        ):
            issues.append("incomplete_quiz_answer")
    settings = get_settings()
    model_review = None
    review_config = None
    runtime_config = runtime_model_registry.get_for_learner(resource.learner_id, "text")
    if manual_status is None and runtime_config is None and settings.llm_mode == "real":
        review_config = await session.scalar(
            select(ModelConfig)
            .where(
                ModelConfig.is_active.is_(True),
                ModelConfig.provider != "mock",
                ModelConfig.model_type.in_(("review", "text")),
            )
            .order_by(ModelConfig.id)
        )
    if manual_status is None and (
        runtime_config is not None or settings.llm_mode == "real"
    ):
        model_review = await get_llm_provider(
            review_config, resource.learner_id
        ).review_resource(
            [
                GeneratedResource(
                    title=resource.title,
                    content=resource.content_markdown,
                    resource_type=resource.resource_type,
                )
            ],
            ModelCallContext(
                task_id=resource.task_id,
                learner_id=resource.learner_id,
                agent_code="resource_review",
                prompt_template_code="resource_review",
                prompt_version=resource.prompt_version,
            ),
        )
    status = manual_status or (
        "needs_revision"
        if issues
        else (model_review.status if model_review else "pass")
    )
    review = ResourceReview(
        review_id=new_id("review"),
        resource_id=resource.resource_id,
        status=status,
        pharmacopoeia_consistency_score=(
            model_review.pharmacopoeia_consistency_score
            if model_review
            else 100
            if "missing_medicine" not in issues
            else 0
        ),
        terminology_accuracy_score=(
            model_review.terminology_accuracy_score
            if model_review
            else 100
            if "empty_content" not in issues
            else 0
        ),
        source_completeness_score=(
            model_review.source_completeness_score
            if model_review
            else 100
            if "missing_evidence" not in issues
            else 0
        ),
        answer_accuracy_score=model_review.answer_accuracy_score
        if model_review
        else 100,
        hallucination_risk_score=model_review.hallucination_risk_score
        if model_review
        else 0
        if not issues
        else 50,
        medical_risk_score=model_review.medical_risk_score
        if model_review
        else 0
        if not issues
        else 50,
        issues_json=issues + (model_review.issues if model_review else []),
        suggestions_json=suggestions
        or (
            model_review.suggestions
            if model_review
            else ["Regenerate with required evidence"]
            if issues
            else []
        ),
        evidence_json=resource.evidence_snapshot_json,
        retrieval_id=resource.retrieval_id,
        citation_validity_score=100 if citation_check["valid"] else 0,
        evidence_coverage_score=100 if resource.evidence_ids_json else 0,
        citation_check_json=citation_check,
        evidence_ids_json=resource.evidence_ids_json,
        data_source=resource.data_source,
        provider=(
            f"{runtime_config.protocol}_compatible"
            if runtime_config
            else review_config.provider
            if review_config
            else "openai_compatible"
        )
        if model_review
        else "mock",
        model_name=(
            runtime_config.model_name
            if runtime_config
            else review_config.model_name
            if review_config
            else settings.review_model
        )
        if model_review
        else "mock-review",
        prompt_version=resource.prompt_version,
        reviewed_at=datetime.now(UTC),
    )
    resource.status = (
        "approved"
        if status == "pass"
        else "needs_revision"
        if status == "needs_revision"
        else "rejected"
        if status == "reject"
        else resource.status
    )
    session.add(review)
    if model_review:
        session.add(
            ModelCallRecord(
                call_id=new_id("mcall"),
                task_id=resource.task_id,
                learner_id=resource.learner_id,
                agent_code="resource_review",
                prompt_template_code="resource_review",
                provider=review.provider,
                model_name=review.model_name,
                call_type="resource_review",
                success=True,
            )
        )
    await session.commit()
    await session.refresh(review)
    return review


def review_data(item: ResourceReview) -> dict:
    return {
        "review_id": item.review_id,
        "resource_id": item.resource_id,
        "status": item.status,
        "pharmacopoeia_consistency_score": item.pharmacopoeia_consistency_score,
        "terminology_accuracy_score": item.terminology_accuracy_score,
        "source_completeness_score": item.source_completeness_score,
        "answer_accuracy_score": item.answer_accuracy_score,
        "hallucination_risk_score": item.hallucination_risk_score,
        "medical_risk_score": item.medical_risk_score,
        "issues": item.issues_json or [],
        "suggestions": item.suggestions_json or [],
        "evidence": item.evidence_json or {},
        "provider": item.provider,
        "reviewed_at": item.reviewed_at,
    }


async def latest_review(session: AsyncSession, resource_id: str) -> ResourceReview:
    item = await session.scalar(
        select(ResourceReview)
        .where(ResourceReview.resource_id == resource_id)
        .order_by(ResourceReview.id.desc())
    )
    if item is None:
        raise NotFoundException("Resource review not found")
    return item
