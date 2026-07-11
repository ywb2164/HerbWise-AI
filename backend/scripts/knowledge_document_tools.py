"""Database-backed command helpers for an explicitly authorised document workflow."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.common.ids import new_id
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.integrations.factory import get_rag_provider
from app.integrations.secrets import SecretResolver
from app.modules.knowledge.rag_models import (
    KnowledgeDataset,
    KnowledgeDocument,
    KnowledgeSyncRecord,
)
from app.modules.resources.models import UploadedFile


async def register(uploaded_file_id: str, dataset_code: str) -> dict[str, object]:
    async with async_session_factory() as session:
        dataset = await session.scalar(
            select(KnowledgeDataset).where(
                KnowledgeDataset.dataset_code == dataset_code,
                KnowledgeDataset.status == "active",
            )
        )
        upload = await session.scalar(
            select(UploadedFile).where(UploadedFile.file_id == uploaded_file_id)
        )
        if dataset is None:
            raise ValueError("active dataset code was not found")
        if upload is None:
            raise ValueError("uploaded_file_id was not found")
        item = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.dataset_id == dataset.id,
                KnowledgeDocument.uploaded_file_id == uploaded_file_id,
            )
        )
        if item is None:
            item = KnowledgeDocument(
                document_code=new_id("doc"),
                dataset_id=dataset.id,
                uploaded_file_id=uploaded_file_id,
                title=upload.original_name,
                document_type=upload.mime_type,
                checksum_sha256=upload.sha256,
                sync_status="registered",
                parse_status="pending",
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
        return {
            "document_code": item.document_code,
            "status": item.sync_status,
            "external_document_id": item.external_document_id,
        }


async def sync(document_code: str) -> dict[str, object]:
    settings = get_settings()
    if not (
        settings.ragflow_base_url
        and settings.ragflow_dataset_id
        and SecretResolver.is_configured("env:RAGFLOW_API_KEY")
    ):
        return {"status": "SKIPPED", "reason": "RAGFlow configuration is missing"}
    async with async_session_factory() as session:
        document = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.document_code == document_code
            )
        )
        if document is None:
            raise ValueError("document code was not found")
        record = KnowledgeSyncRecord(
            sync_id=new_id("sync"),
            document_id=document.id,
            operation="sync",
            status="running",
            request_summary_json={
                "document_code": document.document_code,
                "title": document.title,
            },
        )
        session.add(record)
        await session.flush()
        try:
            response = await get_rag_provider().sync_document(
                {"name": document.title, "document_code": document.document_code}
            )
            data = response.get("data", response) if isinstance(response, dict) else {}
            document.external_document_id = (
                str(
                    data.get("id")
                    or data.get("document_id")
                    or document.external_document_id
                    or ""
                )
                or None
            )
            document.sync_status = "success"
            document.parse_status = str(
                data.get("run") or data.get("status") or "submitted"
            )[:32]
            document.synced_at = datetime.now(UTC)
            document.last_error = None
            record.status, record.response_summary_json = (
                "success",
                {
                    "external_document_id": document.external_document_id,
                    "status": document.parse_status,
                },
            )
        except Exception as exc:
            document.sync_status, document.last_error = "failed", str(exc)[:512]
            record.status, record.error_code, record.error_message = (
                "failed",
                getattr(exc, "error_code", "provider_error"),
                str(exc)[:512],
            )
        record.finished_at = datetime.now(UTC)
        await session.commit()
        return {
            "sync_id": record.sync_id,
            "status": record.status,
            "document_code": document.document_code,
        }


async def check(document_code: str) -> dict[str, object]:
    async with async_session_factory() as session:
        item = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.document_code == document_code
            )
        )
        if item is None:
            raise ValueError("document code was not found")
        return {
            "document_code": item.document_code,
            "external_document_id": item.external_document_id,
            "sync_status": item.sync_status,
            "parse_status": item.parse_status,
            "chunk_count": item.chunk_count,
            "last_error": item.last_error,
        }
