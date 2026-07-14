from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LearningAnswer(Base):
    __tablename__ = "learning_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimension_code: Mapped[str] = mapped_column(String(64), index=True)
    knowledge_point: Mapped[str] = mapped_column(String(255))
    answer_json: Mapped[dict] = mapped_column(JSON)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float, default=0)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LearningTask(Base):
    __tablename__ = "learning_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    learning_task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    task_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="recommended")
    # Legacy rows are path recommendations.  The fields below turn a task into
    # an executable, server-scored learning activity without changing that API.
    source: Mapped[str] = mapped_column(
        String(32), default="manual", server_default="manual"
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    target_dimension_codes_json: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )
    target_knowledge_points_json: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )
    resource_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    learning_path_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recommended_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_medicine_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearningQuestion(Base):
    __tablename__ = "learning_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_code: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    question_type: Mapped[str] = mapped_column(String(32))
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[list] = mapped_column(JSON)
    answer_key: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    dimension_code: Mapped[str] = mapped_column(String(64), index=True)
    knowledge_point: Mapped[str] = mapped_column(String(255), index=True)
    difficulty: Mapped[str] = mapped_column(String(32), index=True)
    medicine_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    review_status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearningTaskQuestion(Base):
    __tablename__ = "learning_task_questions"
    __table_args__ = (
        UniqueConstraint("task_id", "question_id", name="uq_learning_task_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    question_id: Mapped[int] = mapped_column(Integer, index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    score_weight: Mapped[float] = mapped_column(Float, default=1.0)


class LearningTaskAttempt(Base):
    __tablename__ = "learning_task_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LearningTaskAnswer(Base):
    __tablename__ = "learning_task_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "question_id", name="uq_learning_attempt_answer"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(64), index=True)
    question_id: Mapped[int] = mapped_column(Integer, index=True)
    student_answer_json: Mapped[dict] = mapped_column(JSON)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float, default=0)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    dimension_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    knowledge_point: Mapped[str | None] = mapped_column(String(255), nullable=True)
    medicine_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class LearningPath(Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        UniqueConstraint("learner_id", "version", name="uq_learning_path_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="active")
    current_stage: Mapped[str] = mapped_column(String(64))
    path_json: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearningPlan(Base):
    """An auditable, short-horizon plan generated from a learner snapshot.

    ``LearningPath`` remains the existing broad, versioned learning path.  A
    plan is deliberately separate because it has a different lifecycle and
    must preserve the inputs used for a single daily recommendation.
    """

    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    stage: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    daily_minutes: Mapped[int] = mapped_column(Integer)
    total_estimated_minutes: Mapped[int] = mapped_column(Integer)
    profile_snapshot_json: Mapped[dict] = mapped_column(JSON)
    weak_points_snapshot_json: Mapped[list] = mapped_column(JSON)
    recent_performance_snapshot_json: Mapped[dict] = mapped_column(JSON)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_source: Mapped[str] = mapped_column(String(64), default="llm")
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearningPlanItem(Base):
    __tablename__ = "learning_plan_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "order_index", name="uq_learning_plan_item_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(64), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    target_dimensions_json: Mapped[list] = mapped_column(JSON)
    target_knowledge_points_json: Mapped[list] = mapped_column(JSON)
    task_type: Mapped[str] = mapped_column(String(64))
    difficulty: Mapped[str] = mapped_column(String(32))
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    resource_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    linked_task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    linked_resource_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PathReport(Base):
    __tablename__ = "path_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    profile_snapshot_json: Mapped[dict] = mapped_column(JSON)
    weak_points_json: Mapped[list] = mapped_column(JSON)
    path_snapshot_json: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ReportRecord(Base):
    __tablename__ = "report_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    report_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    content_json: Mapped[dict] = mapped_column(JSON)
    file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
