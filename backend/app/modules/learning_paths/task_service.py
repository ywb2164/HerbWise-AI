"""Deterministic, database-backed learning tasks.

This module deliberately has no model, retrieval, or agent dependency: a task
can be completed in a demo/offline deployment using only the database.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, cast
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.exceptions import AppException, NotFoundException
from app.modules.learning_paths.models import (
    LearningEvent,
    LearningQuestion,
    LearningTask,
    LearningTaskAnswer,
    LearningTaskAttempt,
    LearningTaskQuestion,
)
from app.modules.profiles.models import LearnerDimension, LearnerWeakPoint
from app.modules.profiles.rules import score_level
from app.modules.profiles.service import _record_history, require_profile
from app.modules.tasks.models import TaskEvent
from app.modules.traces.models import TraceRecord


class LearningTaskConflict(AppException):
    status_code = 409
    code = 1409


VALID_STATUSES = {
    "pending",
    "in_progress",
    "submitted",
    "completed",
    "expired",
    "cancelled",
}
VALID_QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false"}


def _task_title(dimension: str) -> str:
    labels = {
        "basic_knowledge": "基础知识巩固练习",
        "character_identification": "性状辨识练习",
        "similar_medicine": "相似药材辨析练习",
        "pharmacopoeia_rules": "药典规范练习",
        "clinical_quality_control": "质量控制练习",
        "practical_review": "实践复核练习",
    }
    return labels.get(dimension, "个性化巩固练习")


async def _recent_question_ids(
    session: AsyncSession, learner_id: str, dimension: str
) -> set[int]:
    """Return questions already completed by this learner for one dimension."""
    rows = await session.scalars(
        select(LearningTaskQuestion.question_id)
        .join(
            LearningTask, LearningTask.learning_task_id == LearningTaskQuestion.task_id
        )
        .join(LearningQuestion, LearningQuestion.id == LearningTaskQuestion.question_id)
        .where(
            LearningTask.learner_id == learner_id,
            LearningTask.status == "completed",
            LearningQuestion.dimension_code == dimension,
        )
    )
    return set(rows.all())


def _as_utc_aware(value: datetime) -> datetime:
    """Treat legacy database DATETIME values as UTC before Python arithmetic."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _duration_seconds(started_at: datetime, now: datetime | None = None) -> int:
    completed_at = _as_utc_aware(now or datetime.now(UTC))
    return max(0, int((completed_at - _as_utc_aware(started_at)).total_seconds()))


def _task_data(
    task: LearningTask,
    question_count: int = 0,
    latest_attempt: LearningTaskAttempt | None = None,
) -> dict:
    data: dict[str, Any] = {
        "task_id": task.learning_task_id,
        "title": task.title,
        "task_type": task.task_type,
        "source": task.source or "manual",
        "status": task.status,
        "difficulty": task.difficulty,
        "estimated_minutes": task.estimated_minutes,
        "deadline": task.deadline,
        "progress": 100 if task.status == "completed" else 0,
        "target_dimensions": task.target_dimension_codes_json or [],
        "target_knowledge_points": task.target_knowledge_points_json or [],
        "resource_ids": task.resource_ids_json or [],
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "question_count": question_count,
    }
    if latest_attempt is not None:
        question_results = (latest_attempt.result_json or {}).get(
            "question_results", []
        )
        data["latest_attempt"] = {
            "attempt_id": latest_attempt.attempt_id,
            "submitted_at": latest_attempt.submitted_at,
            "raw_score": latest_attempt.raw_score,
            "accuracy": latest_attempt.accuracy,
            "wrong_count": sum(
                1
                for item in question_results
                if isinstance(item, dict) and item.get("is_correct") is False
            ),
        }
    return data


def _public_question(question: LearningQuestion, link: LearningTaskQuestion) -> dict:
    return {
        "question_id": question.id,
        "question_type": question.question_type,
        "stem": question.stem,
        "options": question.options_json,
        "dimension_code": question.dimension_code,
        "knowledge_point": question.knowledge_point,
        "difficulty": question.difficulty,
        "order_index": link.order_index,
        "score_weight": link.score_weight,
    }


async def _events(
    session: AsyncSession,
    task: LearningTask,
    event_type: str,
    payload: dict,
    *,
    trace_id: str | None = None,
    dimension_code: str | None = None,
    knowledge_point: str | None = None,
) -> None:
    clean = cast(dict[str, Any], json_safe(payload))
    session.add(
        LearningEvent(
            learner_id=task.learner_id,
            event_type=event_type,
            source_type="learning_task",
            source_id=task.learning_task_id,
            dimension_code=dimension_code,
            knowledge_point=knowledge_point,
            payload_json=clean,
            trace_id=trace_id,
        )
    )
    session.add(
        TaskEvent(
            task_id=task.learning_task_id,
            event_type=event_type,
            node_name="deterministic_service",
            status="completed",
            progress=100 if event_type in {"task_completed", "profile_updated"} else 0,
            summary=f"{event_type} completed by deterministic service",
            payload_json={
                "data_source": "database",
                "model": None,
                "prompt_version": None,
                **clean,
            },
        )
    )


async def _task(session: AsyncSession, task_id: str) -> LearningTask:
    item = await session.scalar(
        select(LearningTask).where(LearningTask.learning_task_id == task_id)
    )
    if item is None:
        raise NotFoundException("Learning task not found")
    return item


async def _links(
    session: AsyncSession, task_id: str
) -> list[tuple[LearningTaskQuestion, LearningQuestion]]:
    result = await session.execute(
        select(LearningTaskQuestion, LearningQuestion)
        .join(
            LearningQuestion,
            LearningQuestion.id == LearningTaskQuestion.question_id,
        )
        .where(LearningTaskQuestion.task_id == task_id)
        .order_by(LearningTaskQuestion.order_index)
    )
    return list(result.tuples().all())


async def _create_task(
    session: AsyncSession,
    learner_id: str,
    *,
    dimension: str,
    difficulty: str,
    source: str,
    reason: str,
    task_type: str = "quiz",
    knowledge_point: str | None = None,
) -> LearningTask | None:
    pending = list(
        (
            await session.scalars(
                select(LearningTask).where(
                    LearningTask.learner_id == learner_id,
                    LearningTask.status.in_(("pending", "in_progress")),
                    LearningTask.source == source,
                )
            )
        ).all()
    )
    if any(
        dimension in (item.target_dimension_codes_json or [])
        and (
            knowledge_point is None
            or knowledge_point in (item.target_knowledge_points_json or [])
        )
        for item in pending
    ):
        return next(
            item
            for item in pending
            if dimension in (item.target_dimension_codes_json or [])
            and (
                knowledge_point is None
                or knowledge_point in (item.target_knowledge_points_json or [])
            )
        )
    filters = [
        LearningQuestion.dimension_code == dimension,
        LearningQuestion.difficulty == difficulty,
        LearningQuestion.review_status == "draft",
    ]
    if knowledge_point is not None:
        filters.append(LearningQuestion.knowledge_point == knowledge_point)
    recent_question_ids = await _recent_question_ids(session, learner_id, dimension)
    questions = list(
        (
            await session.scalars(
                select(LearningQuestion)
                .where(*filters, LearningQuestion.id.not_in(recent_question_ids))
                .limit(3)
            )
        ).all()
    )
    if not questions and knowledge_point is None:
        questions = list(
            (
                await session.scalars(
                    select(LearningQuestion)
                    .where(
                        LearningQuestion.dimension_code == dimension,
                        LearningQuestion.review_status == "draft",
                        LearningQuestion.id.not_in(recent_question_ids),
                    )
                    .limit(3)
                )
            ).all()
        )
    if not questions:
        return None
    task = LearningTask(
        learning_task_id=new_id("learn"),
        learner_id=learner_id,
        task_type=task_type,
        title=_task_title(dimension),
        description=reason,
        difficulty=difficulty,
        status="pending",
        source=source,
        estimated_minutes=6,
        target_dimension_codes_json=[dimension],
        target_knowledge_points_json=sorted(
            {item.knowledge_point for item in questions}
        ),
        resource_ids_json=[],
        recommended_reason=reason,
    )
    session.add(task)
    await session.flush()
    for index, question in enumerate(questions, start=1):
        session.add(
            LearningTaskQuestion(
                task_id=task.learning_task_id,
                question_id=question.id,
                order_index=index,
                score_weight=100 / len(questions),
            )
        )
    await _events(
        session,
        task,
        "task_created",
        {"reason": reason, "target_dimensions": [dimension]},
    )
    return task


async def create_task_for_learning_plan(
    session: AsyncSession,
    learner_id: str,
    *,
    dimension: str,
    difficulty: str,
    task_type: str,
    reason: str,
    knowledge_point: str,
) -> LearningTask | None:
    """Create a question-backed task for a validated learning-plan item.

    This intentionally delegates selection and construction to the first
    batch's deterministic task factory.  No answer or scoring logic is
    duplicated here.
    """

    return await _create_task(
        session,
        learner_id,
        dimension=dimension,
        difficulty=difficulty,
        source="learning_plan",
        reason=reason,
        task_type=task_type,
        knowledge_point=knowledge_point,
    )


async def ensure_initial_task(
    session: AsyncSession, learner_id: str
) -> LearningTask | None:
    active = await session.scalar(
        select(LearningTask)
        .where(
            LearningTask.learner_id == learner_id,
            LearningTask.status.in_(("pending", "in_progress")),
        )
        .order_by(LearningTask.id.desc())
    )
    if active is not None:
        return active
    dimensions = list(
        (
            await session.scalars(
                select(LearnerDimension)
                .where(LearnerDimension.learner_id == learner_id)
                .order_by(LearnerDimension.score)
            )
        ).all()
    )
    if not dimensions:
        return None
    dimension = dimensions[0].dimension_code or dimensions[0].dimension_key
    return await _create_task(
        session,
        learner_id,
        dimension=dimension,
        difficulty="basic",
        source="initial_plan",
        reason="当前相对薄弱的能力维度，建议优先巩固。",
    )


async def list_tasks(
    session: AsyncSession,
    learner_id: str,
    status: str | None,
    page: int,
    page_size: int,
) -> dict:
    await require_profile(session, learner_id)
    if status is not None and status not in VALID_STATUSES:
        raise AppException("Invalid learning task status")
    if status is None:
        await ensure_initial_task(session, learner_id)
        await session.commit()
    filters = [LearningTask.learner_id == learner_id]
    if status:
        filters.append(LearningTask.status == status)
    total = (
        await session.scalar(
            select(func.count()).select_from(LearningTask).where(*filters)
        )
        or 0
    )
    records = list(
        (
            await session.scalars(
                select(LearningTask)
                .where(*filters)
                .order_by(LearningTask.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    count_result = await session.execute(
        select(LearningTaskQuestion.task_id, func.count()).group_by(
            LearningTaskQuestion.task_id
        )
    )
    counts: dict[str, int] = {
        str(task_id): int(count) for task_id, count in count_result.tuples().all()
    }
    completed_attempts = list(
        (
            await session.scalars(
                select(LearningTaskAttempt)
                .where(
                    LearningTaskAttempt.learner_id == learner_id,
                    LearningTaskAttempt.status == "completed",
                )
                .order_by(LearningTaskAttempt.id.desc())
            )
        ).all()
    )
    latest_attempts: dict[str, LearningTaskAttempt] = {}
    for item in completed_attempts:
        latest_attempts.setdefault(item.task_id, item)
    return {
        "items": [
            _task_data(
                item,
                int(counts.get(item.learning_task_id, 0)),
                latest_attempts.get(item.learning_task_id),
            )
            for item in records
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


async def task_detail(session: AsyncSession, task_id: str, learner_id: str) -> dict:
    task = await _task(session, task_id)
    if task.learner_id != learner_id:
        raise NotFoundException("Learning task not found")
    links = await _links(session, task_id)
    return {
        **_task_data(task, len(links)),
        "questions": [_public_question(question, link) for link, question in links],
    }


async def start_task(session: AsyncSession, task_id: str, learner_id: str) -> dict:
    task = await _task(session, task_id)
    if task.learner_id != learner_id:
        raise NotFoundException("Learning task not found")
    if task.status in {"completed", "cancelled", "expired"}:
        raise LearningTaskConflict("Task cannot be started in its current status")
    attempt = await session.scalar(
        select(LearningTaskAttempt)
        .where(
            LearningTaskAttempt.task_id == task_id,
            LearningTaskAttempt.learner_id == learner_id,
            LearningTaskAttempt.status == "in_progress",
        )
        .order_by(LearningTaskAttempt.id.desc())
    )
    if attempt is None:
        attempt = LearningTaskAttempt(
            attempt_id=new_id("attempt"),
            task_id=task_id,
            learner_id=learner_id,
            status="in_progress",
        )
        session.add(attempt)
        task.status, task.started_at = "in_progress", datetime.now(UTC)
        trace_id = new_id("trace")
        session.add(
            TraceRecord(
                trace_id=trace_id,
                task_id=task_id,
                learner_id=learner_id,
                trace_data_json={
                    "node_type": "deterministic_service",
                    "data_source": "database",
                    "model": None,
                    "prompt_version": None,
                    "steps": ["learning_task_started"],
                },
            )
        )
        await _events(
            session,
            task,
            "task_started",
            {"attempt_id": attempt.attempt_id},
            trace_id=trace_id,
        )
        await session.commit()
        await session.refresh(attempt)
    links = await _links(session, task_id)
    return {
        "task_id": task_id,
        "attempt_id": attempt.attempt_id,
        "status": "in_progress",
        "started_at": attempt.started_at,
        "questions": [_public_question(question, link) for link, question in links],
    }


def _normalise_answer(question: LearningQuestion, answer: object) -> list[str]:
    values = answer if isinstance(answer, list) else [answer]
    valid = {
        str(item.get("key")) for item in question.options_json if isinstance(item, dict)
    }
    normalised = sorted({str(item).strip() for item in values if str(item).strip()})
    if any(item not in valid for item in normalised):
        raise AppException("Answer contains an invalid option")
    return normalised


async def _update_profile(
    session: AsyncSession,
    task: LearningTask,
    answers: list[tuple[LearningQuestion, bool]],
) -> tuple[list[dict], list[dict]]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    points: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for question, correct in answers:
        grouped[question.dimension_code].append(correct)
        points[(question.dimension_code, question.knowledge_point)].append(correct)
    dimensions = {
        item.dimension_code or item.dimension_key: item
        for item in list(
            (
                await session.scalars(
                    select(LearnerDimension).where(
                        LearnerDimension.learner_id == task.learner_id
                    )
                )
            ).all()
        )
    }
    weight = {"basic": 0.8, "intermediate": 1.0, "advanced": 1.2}.get(
        task.difficulty, 1.0
    )
    changes: list[dict] = []
    for code, outcomes in grouped.items():
        accuracy = sum(outcomes) / len(outcomes)
        base = (
            -3
            if accuracy < 0.4
            else -1
            if accuracy < 0.6
            else 1
            if accuracy < 0.85
            else 3
        )
        delta = max(-4, min(4, round(base * weight)))
        item = dimensions.get(code)
        before = item.score if item else 50
        after = max(0, min(100, before + delta))
        if item is None:
            item = LearnerDimension(
                learner_id=task.learner_id,
                dimension_key=code,
                dimension_code=code,
                score=after,
                level=score_level(after),
                evidence_json={},
            )
            session.add(item)
        else:
            item.score, item.level = after, score_level(after)
        item.evidence_json = {
            **(item.evidence_json or {}),
            "last_task_id": task.learning_task_id,
            "last_accuracy": accuracy,
        }
        change = {
            "dimension_code": code,
            "before": before,
            "after": after,
            "delta": after - before,
            "reason": f"{len(outcomes)} answers at {accuracy:.0%} accuracy",
        }
        changes.append(change)
        await _record_history(
            session,
            task.learner_id,
            "dimension_updated",
            {"score": before},
            {"score": after, "delta": after - before},
            str(change["reason"]),
            task.learning_task_id,
        )
    weak_changes: list[dict] = []
    for (code, point), outcomes in points.items():
        recent = list(
            (
                await session.scalars(
                    select(LearningEvent)
                    .where(
                        LearningEvent.learner_id == task.learner_id,
                        LearningEvent.event_type == "question_answered",
                        LearningEvent.dimension_code == code,
                        LearningEvent.knowledge_point == point,
                    )
                    .order_by(LearningEvent.id.desc())
                    .limit(2)
                )
            ).all()
        )
        previous_wrong = sum(
            1 for event in recent if event.payload_json.get("is_correct") is False
        )
        wrong = sum(1 for item in outcomes if not item)
        record = await session.scalar(
            select(LearnerWeakPoint)
            .where(
                LearnerWeakPoint.learner_id == task.learner_id,
                LearnerWeakPoint.dimension_code == code,
                LearnerWeakPoint.knowledge_point == point,
                LearnerWeakPoint.is_resolved.is_(False),
            )
            .order_by(LearnerWeakPoint.id.desc())
        )
        previous_correct = sum(
            1 for event in recent if event.payload_json.get("is_correct") is True
        )
        if previous_wrong + wrong >= 2:
            severity_before = record.severity if record else None
            if record is None:
                record = LearnerWeakPoint(
                    learner_id=task.learner_id,
                    dimension_code=code,
                    knowledge_point=point,
                    severity="medium",
                    evidence_json={"task_id": task.learning_task_id},
                )
                session.add(record)
            else:
                record.severity = (
                    "high" if record.severity == "medium" else record.severity
                )
            weak_changes.append(
                {
                    "dimension_code": code,
                    "knowledge_point": point,
                    "before": severity_before,
                    "after": record.severity,
                    "reason": "two consecutive incorrect answers",
                }
            )
        elif record is not None and previous_correct + sum(outcomes) >= 3:
            severity_before = record.severity
            record.severity = "medium" if record.severity == "high" else "low"
            weak_changes.append(
                {
                    "dimension_code": code,
                    "knowledge_point": point,
                    "before": severity_before,
                    "after": record.severity,
                    "reason": "three consecutive correct answers",
                }
            )
    await _record_history(
        session,
        task.learner_id,
        "profile_updated",
        None,
        {"dimension_changes": changes, "weak_point_changes": weak_changes},
        "deterministic learning task update",
        task.learning_task_id,
    )
    return changes, weak_changes


async def _next_task(
    session: AsyncSession,
    task: LearningTask,
    accuracy: float,
    answers: list[tuple[LearningQuestion, bool]],
) -> LearningTask | None:
    outcome = defaultdict(list)
    for question, correct in answers:
        outcome[question.dimension_code].append(correct)
    target = (
        min(outcome, key=lambda code: sum(outcome[code]) / len(outcome[code]))
        if outcome
        else (task.target_dimension_codes_json or ["basic_knowledge"])[0]
    )
    difficulty = (
        "basic"
        if accuracy < 0.60
        else "intermediate"
        if accuracy < 0.85
        else "advanced"
    )
    return await _create_task(
        session,
        task.learner_id,
        dimension=target,
        difficulty=difficulty,
        source="adaptive_plan",
        reason=f"根据本次练习 {accuracy:.0%} 的正确率安排后续巩固。",
    )


async def submit_task(
    session: AsyncSession,
    task_id: str,
    learner_id: str,
    attempt_id: str,
    payload_answers: list[dict],
) -> dict:
    task = await _task(session, task_id)
    if task.learner_id != learner_id:
        raise NotFoundException("Learning task not found")
    attempt = await session.scalar(
        select(LearningTaskAttempt).where(LearningTaskAttempt.attempt_id == attempt_id)
    )
    if (
        attempt is None
        or attempt.task_id != task_id
        or attempt.learner_id != learner_id
    ):
        raise AppException("Attempt does not belong to this learner task")
    if attempt.status == "completed" and attempt.result_json:
        return attempt.result_json
    if attempt.status != "in_progress" or task.status in {"cancelled", "expired"}:
        raise LearningTaskConflict("Task attempt cannot be submitted")
    links = await _links(session, task_id)
    expected = {question.id: (link, question) for link, question in links}
    supplied = [item.get("question_id") for item in payload_answers]
    if len(supplied) != len(set(supplied)) or set(supplied) != set(expected):
        raise AppException("Answers must contain every task question exactly once")
    results, profile_answers = [], []
    for answer in payload_answers:
        link, question = expected[answer["question_id"]]
        actual = _normalise_answer(question, answer.get("answer"))
        correct = (
            sorted(
                str(value)
                for value in question.answer_key.get(
                    "values", [question.answer_key.get("value")]
                )
            )
            == actual
        )
        score = float(link.score_weight) if correct else 0.0
        session.add(
            LearningTaskAnswer(
                attempt_id=attempt_id,
                question_id=question.id,
                student_answer_json={"values": actual},
                is_correct=correct,
                score=score,
                feedback=question.explanation,
            )
        )
        await _events(
            session,
            task,
            "question_answered",
            {"attempt_id": attempt_id, "is_correct": correct, "score": score},
            dimension_code=question.dimension_code,
            knowledge_point=question.knowledge_point,
        )
        results.append(
            {
                "question_id": question.id,
                "student_answer": actual
                if question.question_type == "multiple_choice"
                else (actual[0] if actual else None),
                "correct_answer": question.answer_key.get(
                    "values", [question.answer_key.get("value")]
                ),
                "is_correct": correct,
                "score": score,
                "explanation": question.explanation,
            }
        )
        profile_answers.append((question, correct))
    raw_score = round(sum(item["score"] for item in results), 2)
    accuracy = sum(item["is_correct"] for item in results) / len(results)
    now = datetime.now(UTC)
    attempt.status, attempt.submitted_at = "completed", now
    attempt.duration_seconds = _duration_seconds(attempt.started_at, now)
    attempt.raw_score, attempt.final_score, attempt.accuracy = (
        raw_score,
        raw_score,
        accuracy,
    )
    task.status, task.completed_at = "completed", now
    await _events(
        session,
        task,
        "task_completed",
        {"attempt_id": attempt_id, "accuracy": accuracy, "raw_score": raw_score},
    )
    changes, weak_changes = await _update_profile(session, task, profile_answers)
    await _events(
        session,
        task,
        "profile_updated",
        {"dimension_changes": changes, "weak_point_changes": weak_changes},
    )
    next_task = await _next_task(session, task, accuracy, profile_answers)
    if next_task:
        # The adaptive task was just inserted and events are still pending.
        # Flush and reload its scalar columns before synchronous serialization;
        # otherwise an expired attribute access can trigger async I/O outside
        # SQLAlchemy's greenlet context.
        await session.flush()
        await session.refresh(next_task)
    next_data = _task_data(next_task) if next_task else None
    if next_task:
        await _events(
            session,
            task,
            "next_task_created",
            {"next_task_id": next_task.learning_task_id},
        )
    result = {
        "task_id": task_id,
        "attempt_id": attempt_id,
        "status": "completed",
        "raw_score": raw_score,
        "final_score": raw_score,
        "accuracy": accuracy,
        "duration_seconds": attempt.duration_seconds,
        "question_results": results,
        "dimension_changes": changes,
        "weak_point_changes": weak_changes,
        "next_task": next_data,
    }
    attempt.result_json = cast(dict[str, Any], json_safe(result))
    session.add(
        TraceRecord(
            trace_id=new_id("trace"),
            task_id=task_id,
            learner_id=learner_id,
            trace_data_json={
                "node_type": "deterministic_service",
                "data_source": "database",
                "model": None,
                "prompt_version": None,
                "steps": [
                    "learning_task_submitted",
                    "answers_scored",
                    "profile_updated",
                    "next_task_created",
                ],
            },
        )
    )
    await session.commit()
    return result


async def task_result(session: AsyncSession, task_id: str, learner_id: str) -> dict:
    task = await _task(session, task_id)
    if task.learner_id != learner_id:
        raise NotFoundException("Learning task not found")
    attempt = await session.scalar(
        select(LearningTaskAttempt)
        .where(
            LearningTaskAttempt.task_id == task_id,
            LearningTaskAttempt.learner_id == learner_id,
            LearningTaskAttempt.status == "completed",
        )
        .order_by(LearningTaskAttempt.id.desc())
    )
    if attempt is None or not attempt.result_json:
        raise LearningTaskConflict("Task has not been completed")
    return attempt.result_json


async def attempt_result(
    session: AsyncSession, attempt_id: str, learner_id: str
) -> dict:
    """Return exactly one learner-owned completed attempt without starting a task."""
    attempt = await session.scalar(
        select(LearningTaskAttempt).where(
            LearningTaskAttempt.attempt_id == attempt_id,
            LearningTaskAttempt.learner_id == learner_id,
        )
    )
    if attempt is None:
        raise NotFoundException("Learning task attempt not found")
    if attempt.status != "completed" or not attempt.result_json:
        raise LearningTaskConflict("Task attempt has not been completed")
    return attempt.result_json
