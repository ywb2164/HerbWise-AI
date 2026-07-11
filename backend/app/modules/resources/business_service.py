from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.core.exceptions import NotFoundException
from app.integrations.factory import get_llm_provider, get_rag_provider
from app.modules.knowledge.service import find_medicine_by_name, require_medicine
from app.modules.profiles.service import profile_data, require_profile
from app.modules.resources.business_models import (
    PromptTemplate,
    ResourceOutput,
    ResourceReview,
)
from app.modules.resources.business_schemas import GenerateResourceRequest


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
    medicine_match = await find_medicine_by_name(session, payload.medicine_name)
    medicine = await require_medicine(session, medicine_match["id"])
    evidence = [
        item.model_dump()
        for item in await get_rag_provider().retrieve(medicine.standard_name_zh)
    ]
    generated = await get_llm_provider().generate_resource([])
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
    content = f"[mock resource]\n\n# {first.title}\n\n{first.content}\n\nMedicine: {medicine.standard_name_zh}"
    item = ResourceOutput(
        resource_id=resource_id,
        learner_id=payload.learner_id,
        task_id=payload.task_id,
        medicine_id=medicine.id,
        resource_type=payload.resource_type,
        title=first.title,
        content_markdown=content,
        content_json={"mock": True, "parent_resource_id": parent_resource_id},
        difficulty=payload.difficulty,
        status="generated",
        provider="mock",
        model_name="mock-llm",
        prompt_template_id=template.id if template else None,
        prompt_version=template.version if template else "v1",
        profile_snapshot_json=profile_data(profile),
        evidence_snapshot_json={"items": evidence, "data_source": "mock"},
        generation_metadata_json={
            "mode": "mock",
            "generated_at": datetime.now(UTC).isoformat(),
        },
    )
    session.add(item)
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
    issues: list[str] = []
    if not resource.content_markdown.strip():
        issues.append("empty_content")
    if not resource.evidence_snapshot_json:
        issues.append("missing_evidence")
    if resource.medicine_id is None:
        issues.append("missing_medicine")
    if len(resource.content_markdown) > 20000:
        issues.append("abnormal_length")
    status = manual_status or ("pass" if not issues else "needs_revision")
    review = ResourceReview(
        review_id=new_id("review"),
        resource_id=resource.resource_id,
        status=status,
        pharmacopoeia_consistency_score=100 if "missing_medicine" not in issues else 0,
        terminology_accuracy_score=100 if "empty_content" not in issues else 0,
        source_completeness_score=100 if "missing_evidence" not in issues else 0,
        answer_accuracy_score=100,
        hallucination_risk_score=0 if not issues else 50,
        medical_risk_score=0 if not issues else 50,
        issues_json=issues,
        suggestions_json=suggestions
        or (["Regenerate with required evidence"] if issues else []),
        evidence_json=resource.evidence_snapshot_json,
        provider="mock",
        model_name="mock-review",
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
