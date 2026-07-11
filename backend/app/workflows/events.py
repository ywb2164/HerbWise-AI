from app.core.database import async_session_factory
from app.common.json import json_safe
from app.modules.tasks.models import AgentLog, TaskEvent
from app.modules.tasks.repository import add_event, add_log, update_task


async def record_event(
    task_id: str,
    node_name: str,
    status: str,
    progress: int,
    summary: str,
    elapsed_ms: float | None = None,
    payload: dict | None = None,
) -> None:
    async with async_session_factory() as session:
        await add_event(
            session,
            TaskEvent(
                task_id=task_id,
                event_type="node_completed" if status == "success" else "node_started",
                node_name=node_name,
                status=status,
                progress=progress,
                summary=summary,
                payload_json=json_safe(payload),
                elapsed_ms=elapsed_ms,
            ),
        )
        await update_task(session, task_id, current_node=node_name, progress=progress)


async def record_agent_log(
    task_id: str,
    node_name: str,
    status: str,
    elapsed_ms: float,
    output_summary: str,
    error_message: str | None = None,
) -> None:
    async with async_session_factory() as session:
        await add_log(
            session,
            AgentLog(
                task_id=task_id,
                node_name=node_name,
                model_name=None,
                provider="mock",
                prompt_version="v1",
                input_summary=None,
                output_summary=output_summary,
                status=status,
                elapsed_ms=elapsed_ms,
                error_message=error_message,
            ),
        )
