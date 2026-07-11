import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.common.datetime import to_api_datetime
from app.modules.auth.models import User
from app.modules.auth.service import ensure_learner_access, get_current_user
from app.modules.tasks.models import TaskRecord
from app.modules.tasks.schemas import (
    CreateTaskRequest,
    TaskCreatedResponse,
    TaskEventResponse,
    TaskRecordResponse,
)
from app.modules.tasks.service import (
    create_agent_task,
    get_task_events,
    get_task_logs,
    require_task,
)

router = APIRouter(
    prefix="/agent/tasks",
    tags=["agent-tasks"],
    dependencies=[Depends(get_current_user)],
)


def serialize_task(task: TaskRecord) -> TaskRecordResponse:
    return TaskRecordResponse(
        task_id=task.task_id,
        learner_id=task.learner_id,
        task_type=task.task_type,
        status=task.status,
        current_node=task.current_node,
        progress=task.progress,
        result=task.result_json,
        error_message=task.error_message,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.post(
    "",
    response_model=TaskCreatedResponse,
    status_code=202,
    summary="Create agent task",
    description="Create and asynchronously start the fixed mock LangGraph workflow.",
)
async def create_task(
    payload: CreateTaskRequest, user: User = Depends(get_current_user)
) -> TaskCreatedResponse:
    ensure_learner_access(user, payload.learner_id)
    task = await create_agent_task(payload)
    return TaskCreatedResponse(task_id=task.task_id, status=task.status)


@router.get(
    "/{task_id}",
    response_model=TaskRecordResponse,
    summary="Get agent task",
    description="Get current task status and serializable workflow result.",
)
async def get_task(
    task_id: str, user: User = Depends(get_current_user)
) -> TaskRecordResponse:
    task = await require_task(task_id)
    ensure_learner_access(user, task.learner_id)
    return serialize_task(task)


@router.get(
    "/{task_id}/events",
    response_model=list[TaskEventResponse],
    summary="List task events",
    description="List ordered durable workflow events for a task.",
)
async def events(
    task_id: str, user: User = Depends(get_current_user)
) -> list[TaskEventResponse]:
    task = await require_task(task_id)
    ensure_learner_access(user, task.learner_id)
    records = await get_task_events(task_id)
    return [
        TaskEventResponse(
            event=item.event_type,
            task_id=item.task_id,
            node=item.node_name,
            status=item.status,
            progress=item.progress,
            elapsed_ms=item.elapsed_ms,
            summary=item.summary,
            timestamp=item.created_at,
        )
        for item in records
    ]


@router.get(
    "/{task_id}/logs",
    summary="List agent logs",
    description="List redacted per-node agent execution logs.",
)
async def logs(
    task_id: str, user: User = Depends(get_current_user)
) -> list[dict[str, object]]:
    task = await require_task(task_id)
    ensure_learner_access(user, task.learner_id)
    return [
        {
            "node": item.node_name,
            "provider": item.provider,
            "model_name": item.model_name,
            "status": item.status,
            "elapsed_ms": item.elapsed_ms,
            "input_summary": item.input_summary,
            "output_summary": item.output_summary,
            "created_at": to_api_datetime(item.created_at),
        }
        for item in await get_task_logs(task_id)
    ]


@router.get(
    "/{task_id}/stream",
    summary="Stream task events",
    description="Stream workflow events over server-sent events until completion.",
)
async def stream(
    task_id: str, user: User = Depends(get_current_user)
) -> EventSourceResponse:
    task = await require_task(task_id)
    ensure_learner_access(user, task.learner_id)

    async def event_source() -> AsyncIterator[dict[str, str]]:
        sent = 0
        while True:
            records = await get_task_events(task_id)
            for item in records[sent:]:
                payload = TaskEventResponse(
                    event=item.event_type,
                    task_id=item.task_id,
                    node=item.node_name,
                    status=item.status,
                    progress=item.progress,
                    elapsed_ms=item.elapsed_ms,
                    summary=item.summary,
                    timestamp=item.created_at,
                ).model_dump(mode="json")
                yield {
                    "event": item.event_type,
                    "data": json.dumps(payload, ensure_ascii=False),
                }
            sent = len(records)
            task = await require_task(task_id)
            if task.status in {"success", "failed"}:
                return
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_source())
