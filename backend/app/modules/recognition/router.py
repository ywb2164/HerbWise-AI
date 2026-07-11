from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.recognition.schemas import VisionRecognizeRequest
from app.modules.recognition.service import (
    list_records,
    record_data,
    recognize_uploaded_file,
    require_record,
)

router = APIRouter(
    prefix="/vision", tags=["vision"], dependencies=[Depends(get_current_user)]
)


@router.post(
    "/recognize",
    response_model=ApiResponse,
    summary="Recognize an uploaded herb image",
    description="Run the configured mock, Qwen, local, or hybrid recognition path and persist a traceable result.",
)
async def recognize(
    payload: VisionRecognizeRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ensure_learner_access(user, payload.learner_id)
    return success(
        record_data(await recognize_uploaded_file(session, **payload.model_dump()))
    )


@router.get(
    "/records",
    response_model=ApiResponse,
    summary="List vision recognition records",
    description="List persisted recognition records subject to learner data isolation.",
)
async def records(
    learner_id: str | None = None,
    task_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if learner_id is not None:
        ensure_learner_access(user, learner_id)
    elif "student" in {role.code for role in user.roles} and not user.is_superuser:
        learner_id = user.learner_id
    return success(await list_records(session, learner_id, task_id, page, page_size))


@router.get(
    "/records/{recognition_id}",
    response_model=ApiResponse,
    summary="Get vision recognition record",
    description="Return one persisted recognition record including redacted provider outcomes.",
)
async def record(
    recognition_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await require_record(session, recognition_id)
    ensure_learner_access(user, item.learner_id)
    return success(record_data(item))


@router.get(
    "/records/by-task/{task_id}",
    response_model=ApiResponse,
    summary="List recognition records by task",
    description="Return all recognition records associated with a task after access checks.",
)
async def records_by_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    records = await list_records(session, None, task_id, 1, 100)
    for item in records["items"]:
        ensure_learner_access(user, str(item["learner_id"]))
    return success(records)
