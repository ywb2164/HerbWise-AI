from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
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
    consecutive_errors = (
        await session.scalar(
            select(func.count())
            .select_from(LearningAnswer)
            .where(
                LearningAnswer.learner_id == learner_id,
                LearningAnswer.is_correct.is_(False),
            )
        )
        or 0
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
        content_json={
            "data_source": "mock",
            "is_official": False,
            "profile": profile_data(profile),
            "weak_points": await weak_points(session, learner_id),
            "path": path_data(path),
        },
        status="generated",
    )
    session.add(record)
    session.add(
        PathReport(
            report_id=record.report_id,
            learner_id=learner_id,
            profile_snapshot_json=profile_data(profile),
            weak_points_json=await weak_points(session, learner_id),
            path_snapshot_json=path_data(path),
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
