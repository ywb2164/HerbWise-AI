from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.recognition.schemas import VisionRecognizeRequest
from app.modules.recognition.agent_advice import create_recognition_advice_task
from app.core.config import get_settings
from app.modules.recognition.service import (
    list_records,
    record_data,
    recognize_uploaded_file,
    require_record,
    single_name_response_data,
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
    record = await recognize_uploaded_file(session, **payload.model_dump())
    data = single_name_response_data(record)
    mode = get_settings().recognition_agent_mode
    if mode == "async" and record.status == "success":
        agent_task = await create_recognition_advice_task(
            recognition_id=record.recognition_id, learner_id=record.learner_id
        )
        data.update(agent_status="pending", agent_task_id=agent_task.task_id)
    else:
        data["agent_status"] = "skipped" if mode == "off" else "not_started"
    return success(data)


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


@router.post(
    "/records/{recognition_id}/agent-advice",
    response_model=ApiResponse,
    summary="Create optional recognition learning advice",
    description="Create a separate post-recognition assistant task without changing recognition results.",
)
async def create_agent_advice(
    recognition_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await require_record(session, recognition_id)
    ensure_learner_access(user, item.learner_id)
    if get_settings().recognition_agent_mode == "off":
        return success(
            {
                "recognition_id": recognition_id,
                "agent_status": "skipped",
                "agent_task_id": None,
            }
        )
    task = await create_recognition_advice_task(
        recognition_id=recognition_id, learner_id=item.learner_id
    )
    return success(
        {
            "recognition_id": recognition_id,
            "agent_status": "pending",
            "agent_task_id": task.task_id,
        }
    )


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
