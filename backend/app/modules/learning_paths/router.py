from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.learning_paths.service import (
    answer_data,
    create_learning_answer,
    generate_learning_report,
    latest_learning_report,
    latest_path,
    list_learning_answers,
    path_data,
    report_data,
    require_report,
    export_learning_word,
    export_recognition_word,
    report_file_path,
    update_path,
)
from app.modules.profiles.schemas import DimensionCode

paths_router = APIRouter(
    prefix="/learning-paths",
    tags=["learning-paths"],
    dependencies=[Depends(get_current_user)],
)
reports_router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)
answers_router = APIRouter(
    prefix="/learning/answers",
    tags=["learning-answers"],
    dependencies=[Depends(get_current_user)],
)


class LearningAnswerCreate(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    task_id: str | None = Field(default=None, max_length=64)
    question_id: int | None = None
    dimension_code: DimensionCode
    knowledge_point: str = Field(min_length=1, max_length=255)
    answer: dict
    is_correct: bool
    score: float = Field(ge=0, le=100)
    feedback: str | None = None


@answers_router.post(
    "",
    response_model=ApiResponse,
    summary="Submit learning answer",
    description="Persist learner feedback used by deterministic path rules.",
)
async def create_answer(
    payload: LearningAnswerCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, payload.learner_id)
    item = await create_learning_answer(
        session,
        learner_id=payload.learner_id,
        task_id=payload.task_id,
        question_id=payload.question_id,
        dimension_code=payload.dimension_code,
        knowledge_point=payload.knowledge_point,
        answer=payload.answer,
        is_correct=payload.is_correct,
        score=payload.score,
        feedback=payload.feedback,
    )
    return success(answer_data(item))


@answers_router.get(
    "/{learner_id}",
    response_model=ApiResponse,
    summary="List learning answers",
    description="List paginated answer history for one learner.",
)
async def answer_list(
    learner_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(await list_learning_answers(session, learner_id, page, page_size))


@paths_router.post(
    "/update",
    response_model=ApiResponse,
    summary="Update learning path",
    description="Create a new deterministic learning-path version.",
)
async def update(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(path_data(await update_path(session, learner_id)))


@paths_router.get(
    "/{learner_id}",
    response_model=ApiResponse,
    summary="Get current learning path",
    description="Get the latest immutable learning-path version.",
)
async def get_path(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(path_data(await latest_path(session, learner_id)))


@reports_router.post(
    "/learning/{learner_id}/generate",
    response_model=ApiResponse,
    summary="Generate learning report",
    description="Persist a JSON-only mock learning report.",
)
async def generate(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(report_data(await generate_learning_report(session, learner_id)))


@reports_router.get(
    "/learning/{learner_id}",
    response_model=ApiResponse,
    summary="Get latest learning report",
    description="Get the latest JSON-only learning report.",
)
async def get_learning(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(report_data(await latest_learning_report(session, learner_id)))


@reports_router.post(
    "/learning/{learner_id}/export-word",
    response_model=ApiResponse,
    summary="Export learning report as Word",
    description="Generate a controlled Word learning report for the requested learner.",
)
async def export_learning(
    learner_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, learner_id)
    return success(report_data(await export_learning_word(session, learner_id)))


@reports_router.post(
    "/tasks/{task_id}/export-word",
    response_model=ApiResponse,
    summary="Export recognition review as Word",
    description="Generate a controlled Word recognition-review report for one task.",
)
async def export_recognition(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    from app.modules.tasks.service import require_task

    task = await require_task(task_id)
    ensure_learner_access(user, task.learner_id)
    return success(report_data(await export_recognition_word(session, task_id)))


@reports_router.get(
    "/{report_id}",
    response_model=ApiResponse,
    summary="Get report",
    description="Get a persisted report by identifier.",
)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    report = await require_report(session, report_id)
    ensure_learner_access(user, report.learner_id)
    return success(report_data(report))


@reports_router.get(
    "/{report_id}/download",
    summary="Download generated Word report",
    description="Download an existing controlled report file after learner ownership checks.",
)
async def download_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> FileResponse:
    report = await require_report(session, report_id)
    ensure_learner_access(user, report.learner_id)
    path = report_file_path(report)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.name,
    )
