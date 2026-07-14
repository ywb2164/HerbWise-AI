from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.learning_paths.plan_schemas import GenerateLearningPlanPayload
from app.modules.learning_paths.plan_service import (
    current_plan,
    get_plan,
    list_plans,
    transition_plan,
)
from app.workflows.learning_plan_graph import generate_learning_plan

router = APIRouter(
    prefix="/learning-plans",
    tags=["learning-plans"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/generate",
    response_model=ApiResponse,
    summary="Generate personalised learning plan",
    description="Read a learner-owned profile server-side and generate a validated, auditable daily plan.",
)
async def generate(
    payload: GenerateLearningPlanPayload,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, payload.learner_id)
    return success(
        await generate_learning_plan(session, payload.learner_id, payload.daily_minutes)
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="List learning plans",
    description="List the requested learner's saved learning plans in reverse chronological order.",
)
async def list_route(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await list_plans(session, learner_id))


@router.get(
    "/current",
    response_model=ApiResponse,
    summary="Get current learning plan",
    description="Return the learner's current active plan, or null when no active plan exists.",
)
async def current_route(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await current_plan(session, learner_id))


@router.get(
    "/{plan_id}",
    response_model=ApiResponse,
    summary="Get learning plan",
    description="Return one learner-owned plan and its ordered plan items.",
)
async def detail_route(
    plan_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await get_plan(session, plan_id, learner_id))


@router.post(
    "/{plan_id}/activate",
    response_model=ApiResponse,
    summary="Activate learning plan",
    description="Activate a learner-owned plan and close any other active plan for that learner.",
)
async def activate(
    plan_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await transition_plan(session, plan_id, learner_id, "active"))


@router.post(
    "/{plan_id}/cancel",
    response_model=ApiResponse,
    summary="Cancel learning plan",
    description="Cancel a learner-owned plan without changing task scoring or learner dimensions.",
)
async def cancel(
    plan_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await transition_plan(session, plan_id, learner_id, "cancelled"))
