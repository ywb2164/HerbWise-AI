from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.modules.learning_paths.models import (
    LearningEvent,
    LearningQuestion,
    LearningTask,
    LearningTaskAttempt,
    LearningTaskQuestion,
)
from app.modules.learning_paths.task_service import (
    _as_utc_aware,
    _duration_seconds,
    _normalise_answer,
    _public_question,
    submit_task,
)


def _question(question_type: str = "single_choice") -> LearningQuestion:
    return LearningQuestion(
        question_code="contract-question",
        question_type=question_type,
        stem="Question",
        options_json=[{"key": "A", "text": "One"}, {"key": "B", "text": "Two"}],
        answer_key={"value": "A"},
        explanation="Internal explanation",
        dimension_code="basic_knowledge",
        knowledge_point="contract",
        difficulty="basic",
        source="test",
        review_status="draft",
    )


def test_public_learning_question_never_leaks_scoring_fields() -> None:
    question = _question()
    link = LearningTaskQuestion(
        task_id="learn_1", question_id=1, order_index=1, score_weight=10
    )

    payload = _public_question(question, link)

    assert {"answer_key", "correct_answer", "explanation", "is_correct"}.isdisjoint(
        payload
    )
    assert payload["options"] == question.options_json


def test_answer_normalisation_validates_options_and_ignores_choice_order() -> None:
    question = _question("multiple_choice")
    question.options_json.append({"key": "C", "text": "Three"})

    assert _normalise_answer(question, ["C", "A"]) == ["A", "C"]


def test_duration_treats_naive_database_datetime_as_utc() -> None:
    started_at = datetime(2026, 7, 13, 8, 0, 0)
    now = datetime(2026, 7, 13, 8, 2, 30, tzinfo=UTC)

    assert _as_utc_aware(started_at) == started_at.replace(tzinfo=UTC)
    assert _duration_seconds(started_at, now) == 150


def test_duration_accepts_aware_utc_and_other_timezones() -> None:
    utc_started = datetime(2026, 7, 13, 8, 0, 0, tzinfo=UTC)
    offset_started = datetime(
        2026, 7, 13, 16, 0, 0, tzinfo=timezone(timedelta(hours=8))
    )
    now = datetime(2026, 7, 13, 8, 1, 0, tzinfo=UTC)

    assert _duration_seconds(utc_started, now) == 60
    assert _as_utc_aware(offset_started) == utc_started
    assert _duration_seconds(offset_started, now) == 60


def test_duration_never_returns_a_negative_value() -> None:
    now = datetime(2026, 7, 13, 8, 0, 0, tzinfo=UTC)
    future_started_at = datetime(2026, 7, 13, 8, 1, 0)

    assert _duration_seconds(future_started_at, now) == 0


@pytest.mark.asyncio
async def test_repeat_completed_submission_returns_saved_result_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_result = {"task_id": "learn_1", "status": "completed"}
    task = LearningTask(
        learning_task_id="learn_1",
        learner_id="stu_001",
        task_type="quiz",
        title="Quiz",
        difficulty="basic",
        status="completed",
    )
    attempt = LearningTaskAttempt(
        attempt_id="attempt_1",
        task_id="learn_1",
        learner_id="stu_001",
        status="completed",
        result_json=saved_result,
    )

    async def fake_task(*_args: object, **_kwargs: object) -> LearningTask:
        return task

    class Session:
        async def scalar(self, *_args: object) -> LearningTaskAttempt:
            return attempt

    monkeypatch.setattr("app.modules.learning_paths.task_service._task", fake_task)

    assert (
        await submit_task(
            SimpleNamespace(scalar=Session().scalar),
            "learn_1",
            "stu_001",
            "attempt_1",
            [],
        )
        == saved_result
    )


@pytest.mark.asyncio
async def test_submit_refreshes_new_adaptive_task_before_serializing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = LearningTask(
        learning_task_id="learn_1",
        learner_id="stu_001",
        task_type="quiz",
        title="Quiz",
        difficulty="basic",
        status="in_progress",
    )
    attempt = LearningTaskAttempt(
        attempt_id="attempt_1",
        task_id="learn_1",
        learner_id="stu_001",
        status="in_progress",
        started_at=datetime(2026, 7, 13, 8, 0, 0),
    )
    question = _question()
    question.id = 1
    link = LearningTaskQuestion(
        task_id="learn_1", question_id=1, order_index=1, score_weight=100
    )
    next_task = LearningTask(
        learning_task_id="learn_2",
        learner_id="stu_001",
        task_type="quiz",
        title="Follow-up",
        difficulty="advanced",
        status="pending",
        source="adaptive_plan",
        estimated_minutes=6,
        target_dimension_codes_json=["basic_knowledge"],
        target_knowledge_points_json=["contract"],
        resource_ids_json=[],
    )

    class Session:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.operations: list[str] = []

        async def scalar(self, *_args: object) -> LearningTaskAttempt:
            return attempt

        def add(self, item: object) -> None:
            self.added.append(item)

        async def flush(self) -> None:
            self.operations.append("flush")

        async def refresh(self, item: LearningTask) -> None:
            self.operations.append("refresh")
            assert self.operations[-2:] == ["flush", "refresh"]
            item.created_at = datetime(2026, 7, 13, 8, 5, 0)

        async def commit(self) -> None:
            self.operations.append("commit")

    session = Session()

    async def fake_task(*_args: object, **_kwargs: object) -> LearningTask:
        return task

    async def fake_links(
        *_args: object, **_kwargs: object
    ) -> list[tuple[LearningTaskQuestion, LearningQuestion]]:
        return [(link, question)]

    async def fake_profile_update(
        *_args: object, **_kwargs: object
    ) -> tuple[list[dict], list[dict]]:
        return [], []

    async def fake_next_task(*_args: object, **_kwargs: object) -> LearningTask:
        return next_task

    monkeypatch.setattr("app.modules.learning_paths.task_service._task", fake_task)
    monkeypatch.setattr("app.modules.learning_paths.task_service._links", fake_links)
    monkeypatch.setattr(
        "app.modules.learning_paths.task_service._update_profile", fake_profile_update
    )
    monkeypatch.setattr(
        "app.modules.learning_paths.task_service._next_task", fake_next_task
    )

    result = await submit_task(
        session, "learn_1", "stu_001", "attempt_1", [{"question_id": 1, "answer": "A"}]
    )

    assert result["status"] == "completed"
    assert result["next_task"]["task_id"] == "learn_2"
    assert result["next_task"]["created_at"] == next_task.created_at
    assert session.operations == ["flush", "refresh", "commit"]
    assert any(isinstance(item, LearningEvent) for item in session.added)
