from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import (
    ensure_learner_access,
    get_current_user,
    require_role,
)
from app.modules.resources.business_schemas import (
    GenerateResourceRequest,
    ManualDecisionRequest,
    ResourceType,
)
from app.modules.resources.agent_schemas import ResourceGenerationRequest
from app.modules.resources.agent_service import (
    create_job,
    job_data,
    require_job,
    retry_resource,
    run_job_workflow,
)
from app.modules.resources.rag_decision import PROFESSIONAL_RESOURCE_TYPES
from app.modules.resources.business_service import (
    archive_resource,
    generate_resource,
    latest_review,
    list_resources,
    require_resource,
    resource_data,
    review_data,
    review_resource,
)

resources_router = APIRouter(
    prefix="/resources",
    tags=["resources"],
    dependencies=[Depends(get_current_user)],
)
resource_jobs_router = APIRouter(
    prefix="/resource-generation-jobs",
    tags=["resource-generation-jobs"],
    dependencies=[Depends(get_current_user)],
)
reviews_router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
    dependencies=[Depends(get_current_user)],
)


@resources_router.post(
    "/generate",
    response_model=ApiResponse,
    summary="Generate resource",
    description="Persist a mock educational resource with profile and evidence snapshots.",
)
async def generate(
    payload: GenerateResourceRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, payload.learner_id)
    return success(resource_data(await generate_resource(session, payload)))


@resource_jobs_router.post(
    "",
    response_model=ApiResponse,
    status_code=201,
    summary="Generate a personalised learning resource",
    description="Create and synchronously run a persisted resource-generation job from a learner-owned task or plan item.",
)
async def create_generation_job(
    payload: ResourceGenerationRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, payload.learner_id)
    job = await create_job(session, payload)
    await run_job_workflow(session, job, requires_citation=payload.requires_citation)
    return success(job_data(job))


@resource_jobs_router.get(
    "/{job_id}",
    response_model=ApiResponse,
    summary="Get a resource-generation job",
    description="Return the current status and output metadata for a persisted resource-generation job.",
)
async def get_generation_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    job = await require_job(session, job_id)
    ensure_learner_access(user, job.learner_id)
    return success(job_data(job))


@resources_router.get(
    "",
    response_model=ApiResponse,
    summary="List resources",
    description="List persisted resources with pagination.",
)
async def list_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    learner_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if learner_id is not None:
        ensure_learner_access(user, learner_id)
    elif "student" in {role.code for role in user.roles} and not user.is_superuser:
        learner_id = user.learner_id
    return success(await list_resources(session, page, page_size, learner_id))


@resources_router.get(
    "/{resource_id}",
    response_model=ApiResponse,
    summary="Get resource",
    description="Get one persisted resource.",
)
async def get_resource(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    resource = await require_resource(session, resource_id)
    ensure_learner_access(user, resource.learner_id)
    return success(resource_data(resource))


@resources_router.post(
    "/{resource_id}/retry",
    response_model=ApiResponse,
    status_code=201,
    summary="Retry a rejected or failed resource",
    description="Create and run a replacement generation job for a rejected or failed resource.",
)
async def retry(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    resource = await require_resource(session, resource_id)
    ensure_learner_access(user, resource.learner_id)
    job = await retry_resource(session, resource)
    await run_job_workflow(
        session,
        job,
        requires_citation=bool(resource.citation_count)
        or resource.resource_type in PROFESSIONAL_RESOURCE_TYPES,
    )
    return success(job_data(job))


@resources_router.post(
    "/{resource_id}/regenerate",
    response_model=ApiResponse,
    summary="Regenerate resource",
    description="Create a new resource version without replacing the original.",
)
async def regenerate(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    original = await require_resource(session, resource_id)
    ensure_learner_access(user, original.learner_id)
    medicine = await require_resource(session, resource_id)
    del medicine
    from app.modules.knowledge.service import require_medicine

    current_medicine = (
        await require_medicine(session, original.medicine_id)
        if original.medicine_id
        else None
    )
    if current_medicine is None:
        raise ValueError("Resource medicine is required")
    payload = GenerateResourceRequest(
        learner_id=original.learner_id,
        medicine_name=current_medicine.standard_name_zh,
        resource_type=ResourceType(original.resource_type),
        difficulty=original.difficulty,
        task_id=original.task_id,
    )
    return success(
        resource_data(
            await generate_resource(
                session, payload, parent_resource_id=original.resource_id
            )
        )
    )


@resources_router.post(
    "/{resource_id}/archive",
    response_model=ApiResponse,
    summary="Archive resource",
    description="Archive a resource without deleting its history.",
)
async def archive(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    resource = await require_resource(session, resource_id)
    ensure_learner_access(user, resource.learner_id)
    return success(resource_data(await archive_resource(session, resource_id)))


@reviews_router.post(
    "/check",
    response_model=ApiResponse,
    summary="Review resource",
    description="Run deterministic mock content checks and persist the review.",
)
async def check(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    resource = await require_resource(session, resource_id)
    ensure_learner_access(user, resource.learner_id)
    return success(review_data(await review_resource(session, resource_id)))


@reviews_router.get(
    "/{resource_id}",
    response_model=ApiResponse,
    summary="Get resource review",
    description="Get the latest persisted review for a resource.",
)
async def get_review(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    resource = await require_resource(session, resource_id)
    ensure_learner_access(user, resource.learner_id)
    return success(review_data(await latest_review(session, resource_id)))


@reviews_router.post(
    "/{resource_id}/rewrite",
    response_model=ApiResponse,
    summary="Rewrite resource",
    description="Generate a new mock resource version after a revision request.",
)
async def rewrite(
    resource_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    original = await require_resource(session, resource_id)
    ensure_learner_access(user, original.learner_id)
    from app.modules.knowledge.service import require_medicine

    medicine = (
        await require_medicine(session, original.medicine_id)
        if original.medicine_id
        else None
    )
    if medicine is None:
        raise ValueError("Resource medicine is required")
    payload = GenerateResourceRequest(
        learner_id=original.learner_id,
        medicine_name=medicine.standard_name_zh,
        resource_type=ResourceType(original.resource_type),
        difficulty=original.difficulty,
        task_id=original.task_id,
    )
    return success(
        resource_data(
            await generate_resource(
                session, payload, parent_resource_id=original.resource_id
            )
        )
    )


@reviews_router.post(
    "/{resource_id}/manual-decision",
    response_model=ApiResponse,
    summary="Record manual decision",
    description="Allow an administrator or teacher to persist a review decision.",
)
async def manual_decision(
    resource_id: str,
    payload: ManualDecisionRequest,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_role("admin", "teacher")),
):
    return success(
        review_data(
            await review_resource(
                session, resource_id, payload.status, payload.suggestions
            )
        )
    )
