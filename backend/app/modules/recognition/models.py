from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecognitionRecord(Base):
    __tablename__ = "recognition_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    recognition_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    learner_id: Mapped[str] = mapped_column(String(64), index=True)
    file_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    vision_mode: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    final_medicine_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicine_items.id"), nullable=True, index=True
    )
    final_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    agreement_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    local_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    qwen_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fusion_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_failures_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), default="mock")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ModelCallRecord(Base):
    __tablename__ = "model_call_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    learner_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    file_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_code: Mapped[str] = mapped_column(String(64), index=True)
    prompt_template_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    call_type: Mapped[str] = mapped_column(String(32), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    raw_response_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
