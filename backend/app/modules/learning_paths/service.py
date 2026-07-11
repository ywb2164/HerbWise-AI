from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.exceptions import NotFoundException
from app.modules.learning_paths.models import (
    LearningAnswer,
    LearningPath,
    PathReport,
    ReportRecord,
)
from app.modules.learning_paths.rules import build_path
from app.modules.profiles.service import (
    _record_history,
    profile_data,
    profile_dimensions,
    require_profile,
    weak_points,
)


async def update_path(
    session: AsyncSession, learner_id: str, reason: str = "manual_update"
) -> LearningPath:
    await require_profile(session, learner_id)
    dimensions = await profile_dimensions(session, learner_id)
    average = (
        sum(item["score"] for item in dimensions) / len(dimensions)
        if dimensions
        else 0.0
    )
    recent_answers = list(
        (
            await session.scalars(
                select(LearningAnswer)
                .where(LearningAnswer.learner_id == learner_id)
                .order_by(LearningAnswer.id.desc())
                .limit(2)
            )
        ).all()
    )
    consecutive_errors = (
        2
        if len(recent_answers) == 2
        and all(not answer.is_correct for answer in recent_answers)
        and recent_answers[0].knowledge_point == recent_answers[1].knowledge_point
        else 0
    )
    current = await session.scalar(
        select(LearningPath)
        .where(LearningPath.learner_id == learner_id)
        .order_by(LearningPath.version.desc())
    )
    version = (current.version if current else 0) + 1
    result = build_path(average, consecutive_errors)
    item = LearningPath(
        learner_id=learner_id,
        version=version,
        status="active",
        current_stage=result["current_stage"],
        path_json=result,
        reason=reason,
    )
    session.add(item)
    await _record_history(
        session,
        learner_id,
        "learning_path_updated",
        {"version": current.version} if current else None,
        {"version": version, "path": result},
        reason,
    )
    await session.commit()
    await session.refresh(item)
    return item


def path_data(item: LearningPath) -> dict:
    return {
        "learner_id": item.learner_id,
        "version": item.version,
        "status": item.status,
        "current_stage": item.current_stage,
        "path": item.path_json,
        "reason": item.reason,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def latest_path(session: AsyncSession, learner_id: str) -> LearningPath:
    item = await session.scalar(
        select(LearningPath)
        .where(LearningPath.learner_id == learner_id)
        .order_by(LearningPath.version.desc())
    )
    if item is None:
        raise NotFoundException("Learning path not found")
    return item


async def generate_learning_report(
    session: AsyncSession, learner_id: str
) -> ReportRecord:
    profile = await require_profile(session, learner_id)
    path = await latest_path(session, learner_id)
    record = ReportRecord(
        report_id=new_id("report"),
        learner_id=learner_id,
        report_type="learning",
        title="Mock learning report",
        content_json=json_safe(
            {
                "data_source": "mock",
                "is_official": False,
                "profile": profile_data(profile),
                "weak_points": await weak_points(session, learner_id),
                "path": path_data(path),
            }
        ),
        status="generated",
    )
    session.add(record)
    session.add(
        PathReport(
            report_id=record.report_id,
            learner_id=learner_id,
            profile_snapshot_json=json_safe(profile_data(profile)),
            weak_points_json=json_safe(await weak_points(session, learner_id)),
            path_snapshot_json=json_safe(path_data(path)),
            summary="Mock learning-path report",
        )
    )
    await session.commit()
    await session.refresh(record)
    return record


def report_data(item: ReportRecord) -> dict:
    return {
        "report_id": item.report_id,
        "learner_id": item.learner_id,
        "report_type": item.report_type,
        "title": item.title,
        "content": item.content_json,
        "file_id": item.file_id,
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def latest_learning_report(
    session: AsyncSession, learner_id: str
) -> ReportRecord:
    item = await session.scalar(
        select(ReportRecord)
        .where(
            ReportRecord.learner_id == learner_id,
            ReportRecord.report_type == "learning",
        )
        .order_by(ReportRecord.id.desc())
    )
    if item is None:
        raise NotFoundException("Learning report not found")
    return item


async def require_report(session: AsyncSession, report_id: str) -> ReportRecord:
    item = await session.scalar(
        select(ReportRecord).where(ReportRecord.report_id == report_id)
    )
    if item is None:
        raise NotFoundException("Report not found")
    return item


async def create_learning_answer(
    session: AsyncSession,
    *,
    learner_id: str,
    task_id: str | None,
    question_id: int | None,
    dimension_code: str,
    knowledge_point: str,
    answer: dict,
    is_correct: bool,
    score: float,
    feedback: str | None,
) -> LearningAnswer:
    await require_profile(session, learner_id)
    item = LearningAnswer(
        learner_id=learner_id,
        task_id=task_id,
        question_id=question_id,
        dimension_code=dimension_code,
        knowledge_point=knowledge_point,
        answer_json=answer,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


def answer_data(item: LearningAnswer) -> dict:
    return {
        "id": item.id,
        "learner_id": item.learner_id,
        "task_id": item.task_id,
        "question_id": item.question_id,
        "dimension_code": item.dimension_code,
        "knowledge_point": item.knowledge_point,
        "answer": item.answer_json,
        "is_correct": item.is_correct,
        "score": item.score,
        "feedback": item.feedback,
        "submitted_at": item.submitted_at,
    }


async def list_learning_answers(
    session: AsyncSession, learner_id: str, page: int, page_size: int
) -> dict:
    await require_profile(session, learner_id)
    total = (
        await session.scalar(
            select(func.count())
            .select_from(LearningAnswer)
            .where(LearningAnswer.learner_id == learner_id)
        )
        or 0
    )
    records = list(
        (
            await session.scalars(
                select(LearningAnswer)
                .where(LearningAnswer.learner_id == learner_id)
                .order_by(LearningAnswer.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return {
        "items": [answer_data(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }
