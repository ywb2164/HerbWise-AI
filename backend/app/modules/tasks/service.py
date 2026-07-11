import asyncio

from app.common.ids import new_id
from app.core.database import async_session_factory
from app.core.exceptions import AppException
from app.core.exceptions import NotFoundException
from app.modules.tasks.models import TaskRecord
from app.modules.tasks.repository import create_task, get_task, list_events, list_logs
from app.modules.tasks.schemas import CreateTaskRequest
from app.workflows.runner import run_workflow


async def create_agent_task(payload: CreateTaskRequest) -> TaskRecord:
    if payload.vision_mode in {"qwen", "local", "hybrid"} and not payload.file_id:
        raise AppException("Real vision modes require a server-managed file_id")
    task = TaskRecord(
        task_id=new_id("task"),
        learner_id=payload.learner_id,
        task_type=payload.task_type,
        status="queued",
        progress=0,
    )
    async with async_session_factory() as session:
        await create_task(session, task)
    asyncio.create_task(
        run_workflow(
            task.task_id,
            payload.learner_id,
            payload.image_id,
            payload.image_path,
            payload.file_id,
            payload.vision_mode,
            payload.llm_mode,
        )
    )
    return task


async def require_task(task_id: str) -> TaskRecord:
    async with async_session_factory() as session:
        task = await get_task(session, task_id)
        if task is None:
            raise NotFoundException("Task not found")
        return task


async def get_task_events(task_id: str):
    async with async_session_factory() as session:
        return await list_events(session, task_id)


async def get_task_logs(task_id: str):
    async with async_session_factory() as session:
        return await list_logs(session, task_id)
