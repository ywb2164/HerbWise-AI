from __future__ import annotations

from collections import defaultdict
from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.core.exceptions import AppException, NotFoundException
from app.modules.profiles.models import (
    LearnerDimension,
    LearnerHistory,
    LearnerProfile,
    LearnerWeakPoint,
    TestAnswer,
    TestOption,
    TestQuestion,
    TestRecord,
)
from app.modules.profiles.rules import DIMENSION_CODES, diagnose, score_level
from app.modules.profiles.schemas import (
    DimensionCode,
    InitialTestSubmission,
    ProfileCreate,
    ProfileUpdate,
)


class ConflictException(AppException):
    status_code = 409
    code = 1409


def profile_data(profile: LearnerProfile) -> dict:
    return {
        "learner_id": profile.learner_id,
        "user_id": profile.user_id,
        "name": profile.name or profile.display_name,
        "identity_type": profile.identity_type,
        "education_background": profile.education_background,
        "professional_background": profile.professional_background,
        "learning_goal": profile.learning_goal,
        "learning_preference": profile.learning_preference,
        "overall_level": profile.overall_level,
        "diagnosis_summary": profile.diagnosis_summary,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def dimension_data(item: LearnerDimension) -> dict:
    return {
        "dimension_code": item.dimension_code or item.dimension_key,
        "score": item.score,
        "level": item.level or score_level(item.score),
        "evidence_json": item.evidence_json or item.detail_json or {},
        "updated_at": item.updated_at,
    }


async def require_profile(session: AsyncSession, learner_id: str) -> LearnerProfile:
    profile = await session.scalar(
        select(LearnerProfile).where(LearnerProfile.learner_id == learner_id)
    )
    if profile is None:
        raise NotFoundException("Learner profile not found")
    return profile


async def _dimensions(session: AsyncSession, learner_id: str) -> list[LearnerDimension]:
    return list(
        (
            await session.scalars(
                select(LearnerDimension)
                .where(LearnerDimension.learner_id == learner_id)
                .order_by(
                    LearnerDimension.dimension_code, LearnerDimension.dimension_key
                )
            )
        ).all()
    )


async def _record_history(
    session: AsyncSession,
    learner_id: str,
    event_type: str,
    before: dict | None,
    after: dict | None,
    reason: str,
    source_task_id: str | None = None,
) -> None:
    session.add(
        LearnerHistory(
            learner_id=learner_id,
            event_type=event_type,
            before_json=before,
            after_json=after,
            reason=reason,
            source_task_id=source_task_id,
        )
    )


async def _upsert_dimensions(
    session: AsyncSession, learner_id: str, scores: dict[str, float], reason: str
) -> None:
    existing = {
        item.dimension_code or item.dimension_key: item
        for item in await _dimensions(session, learner_id)
    }
    for code, score in scores.items():
        score = float(score)
        if not 0 <= score <= 100:
            raise AppException("Dimension score must be between 0 and 100")
        item = existing.get(code)
        before = dimension_data(item) if item else None
        if item is None:
            item = LearnerDimension(
                learner_id=learner_id,
                dimension_key=code,
                dimension_code=code,
                score=round(score),
                level=score_level(score),
                detail_json={"source": reason},
                evidence_json={"source": reason},
            )
            session.add(item)
        else:
            item.dimension_key = code
            item.dimension_code = code
            item.score = round(score)
            item.level = score_level(score)
            item.evidence_json = {**(item.evidence_json or {}), "source": reason}
        await _record_history(
            session,
            learner_id,
            "dimension_updated",
            before,
            {"dimension_code": code, "score": score, "level": score_level(score)},
            reason,
        )


async def create_profile(
    session: AsyncSession, payload: ProfileCreate
) -> LearnerProfile:
    if await session.scalar(
        select(LearnerProfile.id).where(LearnerProfile.learner_id == payload.learner_id)
    ):
        raise ConflictException("Learner profile already exists")
    profile = LearnerProfile(
        learner_id=payload.learner_id,
        user_id=payload.user_id,
        name=payload.name,
        display_name=payload.name,
        identity_type=payload.identity_type,
        education_background=payload.education_background,
        professional_background=payload.professional_background,
        learning_goal=payload.learning_goal,
        learning_preference=payload.learning_preference,
        overall_level="weak",
        profile_json={"source": "v0.2"},
    )
    session.add(profile)
    await session.flush()
    await _upsert_dimensions(
        session,
        payload.learner_id,
        {
            code: float((payload.dimensions or {}).get(DimensionCode(code), 0))
            for code in DIMENSION_CODES
        },
        "profile_created",
    )
    await _record_history(
        session,
        payload.learner_id,
        "profile_created",
        None,
        {"name": payload.name, "identity_type": payload.identity_type},
        "Profile created",
    )
    await session.commit()
    await session.refresh(profile)
    return profile


async def update_profile(
    session: AsyncSession, learner_id: str, payload: ProfileUpdate
) -> LearnerProfile:
    profile = await require_profile(session, learner_id)
    before = profile_data(profile)
    for key, value in payload.model_dump(
        exclude_unset=True, exclude={"dimensions"}
    ).items():
        setattr(profile, key, value)
        if key == "name":
            profile.display_name = value
    if payload.dimensions is not None:
        await _upsert_dimensions(
            session,
            learner_id,
            {str(code): score for code, score in payload.dimensions.items()},
            "profile_updated",
        )
    await _record_history(
        session,
        learner_id,
        "profile_updated",
        before,
        {
            key: value
            for key, value in payload.model_dump(exclude_unset=True).items()
            if key != "dimensions"
        },
        "Profile updated",
    )
    await session.commit()
    await session.refresh(profile)
    return profile


async def list_profiles(
    session: AsyncSession, page: int, page_size: int, identity_type: str | None
) -> dict:
    filters = [LearnerProfile.identity_type == identity_type] if identity_type else []
    total = (
        await session.scalar(
            select(func.count()).select_from(LearnerProfile).where(*filters)
        )
        or 0
    )
    records = list(
        (
            await session.scalars(
                select(LearnerProfile)
                .where(*filters)
                .order_by(LearnerProfile.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return {
        "items": [profile_data(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


async def profile_dimensions(session: AsyncSession, learner_id: str) -> list[dict]:
    await require_profile(session, learner_id)
    return [dimension_data(item) for item in await _dimensions(session, learner_id)]


async def weak_points(session: AsyncSession, learner_id: str) -> list[dict]:
    await require_profile(session, learner_id)
    records = list(
        (
            await session.scalars(
                select(LearnerWeakPoint)
                .where(LearnerWeakPoint.learner_id == learner_id)
                .order_by(LearnerWeakPoint.created_at.desc())
            )
        ).all()
    )
    return [
        {
            "dimension_code": item.dimension_code,
            "knowledge_point": item.knowledge_point,
            "severity": item.severity,
            "evidence_json": item.evidence_json or {},
            "is_resolved": item.is_resolved,
            "created_at": item.created_at,
            "resolved_at": item.resolved_at,
        }
        for item in records
    ]


async def history(session: AsyncSession, learner_id: str) -> list[dict]:
    await require_profile(session, learner_id)
    records = list(
        (
            await session.scalars(
                select(LearnerHistory)
                .where(LearnerHistory.learner_id == learner_id)
                .order_by(LearnerHistory.created_at.desc())
            )
        ).all()
    )
    return [
        {
            "event_type": item.event_type,
            "before_json": item.before_json,
            "after_json": item.after_json,
            "reason": item.reason,
            "source_task_id": item.source_task_id,
            "created_at": item.created_at,
        }
        for item in records
    ]


async def diagnose_profile(session: AsyncSession, learner_id: str) -> dict:
    profile = await require_profile(session, learner_id)
    dimensions = await _dimensions(session, learner_id)
    scores = {
        item.dimension_code or item.dimension_key: float(item.score)
        for item in dimensions
    }
    point_records = await weak_points(session, learner_id)
    result = diagnose(scores, point_records)
    profile.overall_level = result["overall_level"]
    profile.diagnosis_summary = result["diagnosis_summary"]
    await session.commit()
    return result


async def initial_questions(session: AsyncSession) -> list[dict]:
    questions = list(
        (
            await session.scalars(
                select(TestQuestion)
                .where(TestQuestion.is_active.is_(True))
                .order_by(TestQuestion.question_code)
            )
        ).all()
    )
    options = list(
        (
            await session.scalars(
                select(TestOption).where(
                    TestOption.question_id.in_([q.id for q in questions])
                )
                if questions
                else select(TestOption).where(false())
            )
        ).all()
    )
    by_question: dict[int, list[dict]] = defaultdict(list)
    for option in options:
        by_question[option.question_id].append(
            {
                "key": option.option_key,
                "text": option.option_text,
                "sort_order": option.sort_order,
            }
        )
    return [
        {
            "id": item.id,
            "question_code": item.question_code,
            "dimension_code": item.dimension_code,
            "question_type": item.question_type,
            "stem": item.stem,
            "difficulty": item.difficulty,
            "score": item.score,
            "options": sorted(
                by_question[item.id], key=lambda option: option["sort_order"]
            ),
        }
        for item in questions
    ]


async def submit_initial_test(
    session: AsyncSession, payload: InitialTestSubmission
) -> dict:
    await require_profile(session, payload.learner_id)
    question_ids = [answer.question_id for answer in payload.answers]
    questions = {
        item.id: item
        for item in (
            await session.scalars(
                select(TestQuestion).where(
                    TestQuestion.id.in_(question_ids), TestQuestion.is_active.is_(True)
                )
            )
        ).all()
    }
    if len(questions) != len(set(question_ids)):
        raise AppException("One or more test questions do not exist")
    totals: dict[str, list[float]] = defaultdict(list)
    record_id = new_id("test")
    earned_total = 0.0
    possible_total = 0.0
    for answer in payload.answers:
        question = questions[answer.question_id]
        expected = question.correct_answer_json.get("value")
        actual = answer.answer
        correct = str(actual).strip().casefold() == str(expected).strip().casefold()
        earned = question.score if correct else 0.0
        earned_total += earned
        possible_total += question.score
        totals[question.dimension_code].append(100.0 if correct else 0.0)
        session.add(
            TestAnswer(
                record_id=record_id,
                question_id=question.id,
                answer_json={"value": actual},
                is_correct=correct,
                earned_score=earned,
            )
        )
    dimension_scores = {
        code: round(sum(totals.get(code, [0.0])) / len(totals.get(code, [0.0])), 2)
        for code in DIMENSION_CODES
    }
    session.add(
        TestRecord(
            record_id=record_id,
            learner_id=payload.learner_id,
            test_type="initial",
            total_score=round(earned_total / possible_total * 100, 2)
            if possible_total
            else 0,
            dimension_scores_json=dimension_scores,
        )
    )
    await _upsert_dimensions(
        session, payload.learner_id, dimension_scores, "initial_test_submitted"
    )
    await _record_history(
        session,
        payload.learner_id,
        "initial_test_submitted",
        None,
        {"record_id": record_id, "dimension_scores": dimension_scores},
        "Initial test submitted",
    )
    await session.commit()
    return {
        "record_id": record_id,
        "total_score": round(earned_total / possible_total * 100, 2)
        if possible_total
        else 0,
        "dimension_scores": dimension_scores,
        "diagnosis": await diagnose_profile(session, payload.learner_id),
    }


async def get_test_record(session: AsyncSession, record_id: str) -> dict:
    record = await session.scalar(
        select(TestRecord).where(TestRecord.record_id == record_id)
    )
    if record is None:
        raise NotFoundException("Test record not found")
    answers = list(
        (
            await session.scalars(
                select(TestAnswer).where(TestAnswer.record_id == record_id)
            )
        ).all()
    )
    return {
        "record_id": record.record_id,
        "learner_id": record.learner_id,
        "test_type": record.test_type,
        "total_score": record.total_score,
        "dimension_scores": record.dimension_scores_json,
        "submitted_at": record.submitted_at,
        "answers": [
            {
                "question_id": answer.question_id,
                "answer": answer.answer_json,
                "is_correct": answer.is_correct,
                "earned_score": answer.earned_score,
            }
            for answer in answers
        ],
    }
