from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeDataset(Base):
    __tablename__ = "knowledge_datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dataset_name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(64))
    external_dataset_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="configured")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_datasets.id"), index=True
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_sources.id"), nullable=True
    )
    uploaded_file_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    external_document_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(64))
    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    sync_status: Mapped[str] = mapped_column(String(32), default="registered")
    parse_status: Mapped[str] = mapped_column(String(32), default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    copyright_status: Mapped[str] = mapped_column(String(32), default="unknown")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KnowledgeSyncRecord(Base):
    __tablename__ = "knowledge_sync_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    sync_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id"), index=True
    )
    operation: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    external_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RAGRetrievalRecord(Base):
    __tablename__ = "rag_retrieval_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    retrieval_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    learner_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    dataset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    medicine_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicine_items.id"), nullable=True, index=True
    )
    returned_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    replay_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RAGEvidenceRecord(Base):
    __tablename__ = "rag_evidence_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    retrieval_id: Mapped[str] = mapped_column(String(64), index=True)
    evidence_id: Mapped[str] = mapped_column(String(128), index=True)
    document_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_name: Mapped[str] = mapped_column(String(255))
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_snapshot: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    citation: Mapped[str] = mapped_column(String(512))
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retained_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RAGReplayRecord(Base):
    __tablename__ = "rag_replay_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    replay_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    query_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    evidence_snapshot_json: Mapped[list] = mapped_column(JSON)
    source_retrieval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    medicine_id: Mapped[int | None] = mapped_column(nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), default="identification")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
