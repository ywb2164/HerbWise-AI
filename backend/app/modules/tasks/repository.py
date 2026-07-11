from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.models import AgentLog, TaskEvent, TaskRecord


async def get_task(session: AsyncSession, task_id: str) -> TaskRecord | None:
    return await session.scalar(select(TaskRecord).where(TaskRecord.task_id == task_id))


async def list_events(session: AsyncSession, task_id: str) -> list[TaskEvent]:
    return list(
        (
            await session.scalars(
                select(TaskEvent)
                .where(TaskEvent.task_id == task_id)
                .order_by(TaskEvent.id)
            )
        ).all()
    )


async def list_logs(session: AsyncSession, task_id: str) -> list[AgentLog]:
    return list(
        (
            await session.scalars(
                select(AgentLog)
                .where(AgentLog.task_id == task_id)
                .order_by(AgentLog.id)
            )
        ).all()
    )


async def create_task(session: AsyncSession, task: TaskRecord) -> None:
    session.add(task)
    await session.commit()


async def update_task(session: AsyncSession, task_id: str, **values: object) -> None:
    task = await get_task(session, task_id)
    if task is None:
        return
    for name, value in values.items():
        setattr(task, name, value)
    task.updated_at = datetime.now(UTC)
    await session.commit()


async def add_event(session: AsyncSession, event: TaskEvent) -> None:
    session.add(event)
    await session.commit()


async def add_log(session: AsyncSession, log: AgentLog) -> None:
    session.add(log)
    await session.commit()
