from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True
    )
    education_background: Mapped[str | None] = mapped_column(String(255), nullable=True)
    professional_background: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overall_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    diagnosis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearnerDimension(Base):
    __tablename__ = "learner_dimensions"
    __table_args__ = (
        UniqueConstraint(
            "learner_id", "dimension_code", name="uq_learner_dimension_code"
        ),
        CheckConstraint(
            "score >= 0 AND score <= 100", name="ck_learner_dimension_score"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    dimension_key: Mapped[str] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(Integer, default=0)
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dimension_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearnerWeakPoint(Base):
    __tablename__ = "learner_weak_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    dimension_code: Mapped[str] = mapped_column(String(64), index=True)
    knowledge_point: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LearnerHistory(Base):
    __tablename__ = "learner_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InitialTest(Base):
    __tablename__ = "initial_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TestQuestion(Base):
    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dimension_code: Mapped[str] = mapped_column(String(64), index=True)
    question_type: Mapped[str] = mapped_column(String(32))
    stem: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(32))
    correct_answer_json: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TestOption(Base):
    __tablename__ = "test_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_key", name="uq_test_option_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(Integer, index=True)
    option_key: Mapped[str] = mapped_column(String(16))
    option_text: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0)


class TestRecord(Base):
    __tablename__ = "test_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    test_type: Mapped[str] = mapped_column(String(32))
    total_score: Mapped[float] = mapped_column(Float, default=0)
    dimension_scores_json: Mapped[dict] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TestAnswer(Base):
    __tablename__ = "test_answers"
    __table_args__ = (
        UniqueConstraint("record_id", "question_id", name="uq_test_answer_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[str] = mapped_column(String(64), index=True)
    question_id: Mapped[int] = mapped_column(Integer, index=True)
    answer_json: Mapped[dict] = mapped_column(JSON)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    earned_score: Mapped[float] = mapped_column(Float, default=0)
