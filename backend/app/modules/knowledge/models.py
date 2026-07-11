from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MedicineItem(Base):
    __tablename__ = "medicine_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    standard_name_zh: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    standard_name_en: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    training_class_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    latin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties_flavor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meridian_tropism: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MedicineAlias(Base):
    __tablename__ = "medicine_aliases"
    __table_args__ = (
        UniqueConstraint(
            "medicine_id", "normalized_name", name="uq_medicine_alias_normalized"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_items.id", ondelete="CASCADE"), index=True
    )
    alias_name: Mapped[str] = mapped_column(String(128))
    alias_type: Mapped[str] = mapped_column(String(32), default="common")
    language: Mapped[str] = mapped_column(String(16), default="zh")
    normalized_name: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32))
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    copyright_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="demo_seed_data")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MedicineFeature(Base):
    __tablename__ = "medicine_features"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_items.id", ondelete="CASCADE"), index=True
    )
    feature_type: Mapped[str] = mapped_column(String(32), index=True)
    feature_name: Mapped[str] = mapped_column(String(128))
    feature_value: Mapped[str] = mapped_column(Text)
    evidence_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_sources.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SimilarMedicine(Base):
    __tablename__ = "similar_medicines"
    __table_args__ = (
        UniqueConstraint(
            "medicine_id", "similar_medicine_id", name="uq_similar_medicine_pair"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_items.id", ondelete="CASCADE"), index=True
    )
    similar_medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_items.id", ondelete="CASCADE"), index=True
    )
    confusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    distinguishing_features_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KnowledgeChunkMapping(Base):
    __tablename__ = "knowledge_chunk_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_items.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True
    )
    external_dataset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_document_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_chunk_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
