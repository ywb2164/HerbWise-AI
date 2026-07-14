"""Optional post-recognition learning assistance.

This module intentionally consumes a persisted recognition snapshot and never
calls the vision pipeline or mutates ``RecognitionRecord``.  It keeps the
legacy full-loop workflow available elsewhere while giving the recognition
screen a small, independently observable assistant task.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.database import async_session_factory
from app.core.exceptions import NotFoundException
from app.modules.recognition.models import RecognitionRecord
from app.modules.tasks.models import TaskRecord
from app.modules.tasks.repository import create_task, update_task
from app.modules.traces.models import TraceRecord
from app.workflows.events import record_agent_log, record_event


def _advice_from_snapshot(record: RecognitionRecord) -> dict[str, object]:
    fusion = record.fusion_result_json or {}
    final = fusion.get("final_identification") or {}
    display_name = str(final.get("display_name_zh") or record.final_name or "该药材")
    catalog_status = str(final.get("catalog_status") or "out_of_catalog")
    actions: list[dict[str, str]] = [
        {"type": "review_image", "title": f"复看{display_name}的外形与纹理"},
    ]
    if catalog_status == "matched":
        actions.append({"type": "view_knowledge", "title": f"查看{display_name}知识卡"})
    else:
        actions.append(
            {"type": "capture_clearer_image", "title": "补充清晰的局部与断面图片"}
        )
    return {
        "summary": f"已完成{display_name}辨识。建议结合外形、表面纹理与药用部位进行复核学习。",
        "learning_dimension": "appearance_identification",
        "recommended_actions": actions,
        "citation_available": False,
    }


async def create_recognition_advice_task(
    *, recognition_id: str, learner_id: str
) -> TaskRecord:
    task = TaskRecord(
        task_id=new_id("agent"),
        learner_id=learner_id,
        task_type="recognition_agent_advice",
        status="queued",
        progress=0,
        result_json={"recognition_id": recognition_id},
    )
    async with async_session_factory() as session:
        await create_task(session, task)
    asyncio.create_task(
        run_recognition_advice(task.task_id, recognition_id, learner_id)
    )
    return task


async def run_recognition_advice(
    task_id: str, recognition_id: str, learner_id: str
) -> None:
    try:
        async with async_session_factory() as session:
            await update_task(
                session,
                task_id,
                status="running",
                current_node="load_recognition_context",
                progress=0,
                started_at=datetime.now(UTC),
            )
            record = await session.scalar(
                select(RecognitionRecord).where(
                    RecognitionRecord.recognition_id == recognition_id,
                    RecognitionRecord.learner_id == learner_id,
                )
            )
            if record is None:
                raise NotFoundException("Recognition record not found")
            snapshot = {
                "recognition_id": record.recognition_id,
                "final_identification": (record.fusion_result_json or {}).get(
                    "final_identification"
                ),
            }
        await record_event(
            task_id,
            "load_recognition_context",
            "success",
            30,
            "recognition snapshot loaded",
            payload=snapshot,
            event_type="agent.recognition_context.loaded",
        )
        advice = _advice_from_snapshot(record)
        await record_event(
            task_id,
            "generate_learning_advice",
            "success",
            75,
            "learning advice generated",
            payload=advice,
            event_type="agent.learning_advice.generated",
        )
        trace = TraceRecord(
            trace_id=new_id("trace"),
            task_id=task_id,
            learner_id=learner_id,
            trace_data_json={
                "trace_kind": "recognition_agent",
                "recognition_id": recognition_id,
                "parent_trace_id": None,
                "nodes": [
                    "load_recognition_context",
                    "generate_learning_advice",
                    "persist_agent_result",
                ],
            },
        )
        async with async_session_factory() as session:
            session.add(trace)
            await session.commit()
            await update_task(
                session,
                task_id,
                status="success",
                current_node="persist_agent_result",
                progress=100,
                result_json=json_safe(
                    {
                        "recognition_id": recognition_id,
                        "agent_result": advice,
                        "trace_id": trace.trace_id,
                    }
                ),
                finished_at=datetime.now(UTC),
            )
        await record_event(
            task_id,
            "persist_agent_result",
            "success",
            100,
            "assistant result persisted",
            event_type="agent.result.persisted",
        )
        await record_agent_log(
            task_id,
            "generate_learning_advice",
            "success",
            0,
            "deterministic recognition guidance generated",
        )
    except Exception as exc:
        async with async_session_factory() as session:
            await update_task(
                session,
                task_id,
                status="failed",
                error_message=str(exc)[:512],
                finished_at=datetime.now(UTC),
            )
        await record_event(
            task_id,
            "generate_learning_advice",
            "failed",
            100,
            "learning advice generation failed",
            payload={"error": str(exc)[:512]},
            event_type="agent.learning_advice.failed",
        )
