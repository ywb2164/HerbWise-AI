from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.service import get_current_user, require_role
from app.modules.resources.business_schemas import (
    GenerateResourceRequest,
    ManualDecisionRequest,
    ResourceType,
)
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
    payload: GenerateResourceRequest, session: AsyncSession = Depends(get_session)
):
    return success(resource_data(await generate_resource(session, payload)))


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
):
    return success(await list_resources(session, page, page_size, learner_id))


@resources_router.get(
    "/{resource_id}",
    response_model=ApiResponse,
    summary="Get resource",
    description="Get one persisted resource.",
)
async def get_resource(resource_id: str, session: AsyncSession = Depends(get_session)):
    return success(resource_data(await require_resource(session, resource_id)))


@resources_router.post(
    "/{resource_id}/regenerate",
    response_model=ApiResponse,
    summary="Regenerate resource",
    description="Create a new resource version without replacing the original.",
)
async def regenerate(resource_id: str, session: AsyncSession = Depends(get_session)):
    original = await require_resource(session, resource_id)
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
async def archive(resource_id: str, session: AsyncSession = Depends(get_session)):
    return success(resource_data(await archive_resource(session, resource_id)))


@reviews_router.post(
    "/check",
    response_model=ApiResponse,
    summary="Review resource",
    description="Run deterministic mock content checks and persist the review.",
)
async def check(resource_id: str, session: AsyncSession = Depends(get_session)):
    return success(review_data(await review_resource(session, resource_id)))


@reviews_router.get(
    "/{resource_id}",
    response_model=ApiResponse,
    summary="Get resource review",
    description="Get the latest persisted review for a resource.",
)
async def get_review(resource_id: str, session: AsyncSession = Depends(get_session)):
    return success(review_data(await latest_review(session, resource_id)))


@reviews_router.post(
    "/{resource_id}/rewrite",
    response_model=ApiResponse,
    summary="Rewrite resource",
    description="Generate a new mock resource version after a revision request.",
)
async def rewrite(resource_id: str, session: AsyncSession = Depends(get_session)):
    original = await require_resource(session, resource_id)
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
