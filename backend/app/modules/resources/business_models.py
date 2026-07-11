from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    task_type: Mapped[str] = mapped_column(String(64))
    system_prompt: Mapped[str] = mapped_column(Text)
    user_prompt_template: Mapped[str] = mapped_column(Text)
    output_schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="v1")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResourceOutput(Base):
    __tablename__ = "resource_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    medicine_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicine_items.id"), nullable=True, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content_markdown: Mapped[str] = mapped_column(Text)
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="mock")
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompt_templates.id"), nullable=True
    )
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    profile_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retrieval_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    evidence_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    citations_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), default="mock")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(64), index=True)
    question_type: Mapped[str] = mapped_column(String(32))
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correct_answer_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(32))
    dimension_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    knowledge_point: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ResourceReview(Base):
    __tablename__ = "resource_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    pharmacopoeia_consistency_score: Mapped[float] = mapped_column(default=0)
    terminology_accuracy_score: Mapped[float] = mapped_column(default=0)
    source_completeness_score: Mapped[float] = mapped_column(default=0)
    answer_accuracy_score: Mapped[float] = mapped_column(default=0)
    hallucination_risk_score: Mapped[float] = mapped_column(default=0)
    medical_risk_score: Mapped[float] = mapped_column(default=0)
    issues_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggestions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="mock")
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieval_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    citation_validity_score: Mapped[float] = mapped_column(default=0)
    evidence_coverage_score: Mapped[float] = mapped_column(default=0)
    citation_check_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), default="mock")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
