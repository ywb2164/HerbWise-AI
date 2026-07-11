from datetime import UTC, datetime

from app.core.database import async_session_factory
from app.common.json import json_safe
from app.modules.tasks.repository import update_task
from app.workflows.graph import workflow


async def run_workflow(
    task_id: str,
    learner_id: str,
    image_id: str | None,
    image_path: str | None,
    file_id: str | None = None,
    vision_mode: str | None = None,
    llm_mode: str | None = None,
) -> None:
    async with async_session_factory() as session:
        await update_task(
            session,
            task_id,
            status="running",
            started_at=datetime.now(UTC),
            current_node="load_profile",
            progress=0,
        )
    try:
        result = await workflow.ainvoke(
            {
                "task_id": task_id,
                "learner_id": learner_id,
                "image_id": image_id,
                "image_path": image_path,
                "file_id": file_id,
                "vision_mode": vision_mode,
                "llm_mode": llm_mode,
                "persistence_enabled": True,
                "retry_count": 0,
                "errors": [],
            }
        )
    except Exception as exc:
        async with async_session_factory() as session:
            await update_task(
                session,
                task_id,
                status="failed",
                error_message=str(exc),
                finished_at=datetime.now(UTC),
            )
        return
    async with async_session_factory() as session:
        await update_task(
            session,
            task_id,
            status="success",
            current_node="save_trace",
            progress=100,
            result_json=json_safe(dict(result)),
            finished_at=datetime.now(UTC),
        )
