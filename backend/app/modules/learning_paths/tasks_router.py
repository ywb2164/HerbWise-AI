from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.learning_paths.task_service import (
    attempt_result,
    list_tasks,
    start_task,
    submit_task,
    task_detail,
    task_result,
)


router = APIRouter(
    prefix="/learning-tasks",
    tags=["learning-tasks"],
    dependencies=[Depends(get_current_user)],
)


class TaskAnswerPayload(BaseModel):
    question_id: int
    answer: str | list[str] | None = None


class SubmitTaskPayload(BaseModel):
    attempt_id: str = Field(min_length=1, max_length=64)
    answers: list[TaskAnswerPayload] = Field(min_length=1, max_length=20)


@router.get(
    "",
    response_model=ApiResponse,
    summary="List learning tasks",
    description="List only the requested learner's deterministic learning tasks.",
)
async def list_route(
    learner_id: str,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await list_tasks(session, learner_id, status, page, page_size))


@router.get(
    "/attempts/{attempt_id}/result",
    response_model=ApiResponse,
    summary="Get one completed learner task attempt",
    description="Return the result of a completed learner task attempt for the selected learner.",
)
async def attempt_result_route(
    attempt_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await attempt_result(session, attempt_id, learner_id))


@router.get(
    "/{task_id}",
    response_model=ApiResponse,
    summary="Get learning task",
    description="Return task questions without answer keys, explanations, or scoring data.",
)
async def detail_route(
    task_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await task_detail(session, task_id, learner_id))


@router.post(
    "/{task_id}/start",
    response_model=ApiResponse,
    summary="Start learning task",
    description="Create or resume the learner's single active task attempt.",
)
async def start_route(
    task_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await start_task(session, task_id, learner_id))


@router.post(
    "/{task_id}/submit",
    response_model=ApiResponse,
    summary="Submit learning task",
    description="Validate answers, score server-side, update the profile, and recommend a next task.",
)
async def submit_route(
    task_id: str,
    payload: SubmitTaskPayload,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(
        await submit_task(
            session,
            task_id,
            learner_id,
            payload.attempt_id,
            [item.model_dump() for item in payload.answers],
        )
    )


@router.get(
    "/{task_id}/result",
    response_model=ApiResponse,
    summary="Get learning task result",
    description="Return the persisted result of a completed learner-owned task.",
)
async def result_route(
    task_id: str,
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await task_result(session, task_id, learner_id))
