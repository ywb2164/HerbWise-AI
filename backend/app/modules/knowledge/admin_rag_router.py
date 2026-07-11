from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.core.database import get_session
from app.core.exceptions import AppException, NotFoundException
from app.core.responses import ApiResponse, success
from app.modules.auth.service import require_role
from app.modules.knowledge.rag_models import (
    KnowledgeDataset,
    KnowledgeDocument,
    KnowledgeSyncRecord,
    RAGEvidenceRecord,
    RAGReplayRecord,
    RAGRetrievalRecord,
)
from app.modules.resources.models import UploadedFile
from app.modules.knowledge.rag_service import _fingerprint
from app.integrations.contracts import RAGQuery
from app.core.config import get_settings

router = APIRouter(
    prefix="/admin", tags=["admin-rag"], dependencies=[Depends(require_role("admin"))]
)


class DatasetWrite(BaseModel):
    dataset_code: str = Field(min_length=1, max_length=64)
    dataset_name: str = Field(min_length=1, max_length=255)
    provider: str = Field(default="ragflow", max_length=64)
    external_dataset_id: str | None = Field(default=None, max_length=128)
    status: str = Field(default="active", pattern="^(active|disabled|error)$")
    is_default: bool = False
    config: dict | None = None


def dataset_data(item: KnowledgeDataset) -> dict:
    return {
        "id": item.id,
        "dataset_code": item.dataset_code,
        "dataset_name": item.dataset_name,
        "provider": item.provider,
        "external_dataset_id": item.external_dataset_id,
        "status": item.status,
        "is_default": item.is_default,
        "config": item.config_json or {},
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def _dataset(session: AsyncSession, dataset_id: int) -> KnowledgeDataset:
    item = await session.get(KnowledgeDataset, dataset_id)
    if item is None:
        raise NotFoundException("Knowledge dataset not found")
    return item


@router.post(
    "/knowledge/datasets",
    response_model=ApiResponse,
    summary="Create knowledge dataset",
    description="Register a safe dataset reference without credentials.",
)
async def create_dataset(
    payload: DatasetWrite, session: AsyncSession = Depends(get_session)
):
    if payload.external_dataset_id and await session.scalar(
        select(KnowledgeDataset.id).where(
            KnowledgeDataset.external_dataset_id == payload.external_dataset_id
        )
    ):
        raise AppException("External dataset ID already exists", code=1409)
    if payload.is_default:
        for item in (
            await session.scalars(
                select(KnowledgeDataset).where(KnowledgeDataset.is_default.is_(True))
            )
        ).all():
            item.is_default = False
    item = KnowledgeDataset(
        dataset_code=payload.dataset_code,
        dataset_name=payload.dataset_name,
        provider=payload.provider,
        external_dataset_id=payload.external_dataset_id,
        status=payload.status,
        is_default=payload.is_default,
        config_json=payload.config,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return success(dataset_data(item))


@router.get(
    "/knowledge/datasets",
    response_model=ApiResponse,
    summary="List knowledge datasets",
    description="List registered datasets without credentials.",
)
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    total = (
        await session.scalar(select(func.count()).select_from(KnowledgeDataset)) or 0
    )
    items = list(
        (
            await session.scalars(
                select(KnowledgeDataset)
                .order_by(KnowledgeDataset.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return success(
        {
            "items": [dataset_data(item) for item in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    )


@router.post(
    "/knowledge/datasets/{dataset_id}/set-default",
    response_model=ApiResponse,
    summary="Set default dataset",
    description="Set one active dataset as the sole default.",
)
async def set_default(dataset_id: int, session: AsyncSession = Depends(get_session)):
    item = await _dataset(session, dataset_id)
    if item.status != "active":
        raise AppException("Only active datasets can be default")
    for other in (
        await session.scalars(
            select(KnowledgeDataset).where(KnowledgeDataset.is_default.is_(True))
        )
    ).all():
        other.is_default = False
    item.is_default = True
    await session.commit()
    await session.refresh(item)
    return success(dataset_data(item))


@router.post(
    "/knowledge/datasets/{dataset_id}/disable",
    response_model=ApiResponse,
    summary="Disable knowledge dataset",
    description="Disable future use without deleting retrieval history.",
)
async def disable_dataset(
    dataset_id: int, session: AsyncSession = Depends(get_session)
):
    item = await _dataset(session, dataset_id)
    item.status = "disabled"
    item.is_default = False
    await session.commit()
    return success(dataset_data(item))


@router.get(
    "/knowledge/datasets/{dataset_id}",
    response_model=ApiResponse,
    summary="Get knowledge dataset",
    description="Get safe dataset metadata.",
)
async def get_dataset(dataset_id: int, session: AsyncSession = Depends(get_session)):
    return success(dataset_data(await _dataset(session, dataset_id)))


@router.put(
    "/knowledge/datasets/{dataset_id}",
    response_model=ApiResponse,
    summary="Update knowledge dataset",
    description="Update safe dataset metadata without credentials.",
)
async def update_dataset(
    dataset_id: int, payload: DatasetWrite, session: AsyncSession = Depends(get_session)
):
    item = await _dataset(session, dataset_id)
    for key, value in payload.model_dump().items():
        setattr(item, "config_json" if key == "config" else key, value)
    await session.commit()
    await session.refresh(item)
    return success(dataset_data(item))


def document_data(item: KnowledgeDocument) -> dict:
    return {
        "id": item.id,
        "document_code": item.document_code,
        "dataset_id": item.dataset_id,
        "uploaded_file_id": item.uploaded_file_id,
        "external_document_id": item.external_document_id,
        "title": item.title,
        "document_type": item.document_type,
        "sync_status": item.sync_status,
        "parse_status": item.parse_status,
        "chunk_count": item.chunk_count,
        "copyright_status": item.copyright_status,
        "is_active": item.is_active,
    }


class DocumentWrite(BaseModel):
    document_code: str = Field(min_length=1, max_length=64)
    dataset_id: int
    uploaded_file_id: str
    title: str = Field(min_length=1, max_length=255)
    document_type: str = Field(default="text", max_length=64)
    copyright_status: str = Field(default="unknown", max_length=32)


@router.post(
    "/knowledge/documents",
    response_model=ApiResponse,
    summary="Register knowledge document",
    description="Register a validated uploaded document without automatically synchronizing it.",
)
async def create_document(
    payload: DocumentWrite, session: AsyncSession = Depends(get_session)
):
    dataset = await _dataset(session, payload.dataset_id)
    if dataset.status != "active":
        raise AppException("Dataset is not active")
    file = await session.scalar(
        select(UploadedFile).where(UploadedFile.file_id == payload.uploaded_file_id)
    )
    if file is None:
        raise NotFoundException("Uploaded file not found")
    if file.mime_type not in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    }:
        raise AppException("Unsupported knowledge document MIME type")
    existing = await session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.dataset_id == payload.dataset_id,
            KnowledgeDocument.checksum_sha256 == file.sha256,
        )
    )
    if existing:
        return success(document_data(existing))
    item = KnowledgeDocument(
        document_code=payload.document_code,
        dataset_id=payload.dataset_id,
        uploaded_file_id=file.file_id,
        title=payload.title,
        document_type=payload.document_type,
        checksum_sha256=file.sha256,
        copyright_status=payload.copyright_status,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return success(document_data(item))


@router.get(
    "/knowledge/documents",
    response_model=ApiResponse,
    summary="List knowledge documents",
    description="List document metadata without revealing server paths or document bodies.",
)
async def list_documents(session: AsyncSession = Depends(get_session)):
    return success(
        [
            document_data(item)
            for item in (
                await session.scalars(
                    select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())
                )
            ).all()
        ]
    )


@router.post(
    "/knowledge/documents/{document_id}/sync",
    response_model=ApiResponse,
    summary="Start document synchronization",
    description="Record one explicit synchronization attempt; provider calls are never implicit.",
)
async def sync_document(document_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(KnowledgeDocument, document_id)
    if item is None or not item.is_active:
        raise NotFoundException("Active knowledge document not found")
    record = KnowledgeSyncRecord(
        sync_id=new_id("sync"),
        document_id=item.id,
        operation="sync",
        status="syncing",
        request_summary_json={"document_code": item.document_code},
    )
    item.sync_status = "syncing"
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return success({"sync_id": record.sync_id, "status": record.status})


@router.post(
    "/knowledge/documents/{document_id}/retry",
    response_model=ApiResponse,
    summary="Retry document synchronization",
    description="Create a new synchronization attempt for the same registered document.",
)
async def retry_document(
    document_id: int, session: AsyncSession = Depends(get_session)
):
    return await sync_document(document_id, session)


@router.get(
    "/knowledge/documents/{document_id}/sync-records",
    response_model=ApiResponse,
    summary="List document synchronization records",
    description="Return safe synchronization status history.",
)
async def sync_records(document_id: int, session: AsyncSession = Depends(get_session)):
    records = list(
        (
            await session.scalars(
                select(KnowledgeSyncRecord).where(
                    KnowledgeSyncRecord.document_id == document_id
                )
            )
        ).all()
    )
    return success(
        [
            {
                "sync_id": item.sync_id,
                "operation": item.operation,
                "status": item.status,
                "error_code": item.error_code,
                "error_message": item.error_message,
                "started_at": item.started_at,
                "finished_at": item.finished_at,
            }
            for item in records
        ]
    )


@router.post(
    "/knowledge/documents/{document_id}/disable",
    response_model=ApiResponse,
    summary="Disable knowledge document",
    description="Disable a document without deleting synchronization or evidence history.",
)
async def disable_document(
    document_id: int, session: AsyncSession = Depends(get_session)
):
    item = await session.get(KnowledgeDocument, document_id)
    if item is None:
        raise NotFoundException("Knowledge document not found")
    item.is_active = False
    item.sync_status = "disabled"
    item.parse_status = "disabled"
    await session.commit()
    return success(document_data(item))


@router.get(
    "/knowledge/documents/{document_id}",
    response_model=ApiResponse,
    summary="Get knowledge document",
    description="Get one document metadata record.",
)
async def get_document(document_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(KnowledgeDocument, document_id)
    if item is None:
        raise NotFoundException("Knowledge document not found")
    return success(document_data(item))


@router.post(
    "/knowledge/documents/{document_id}/refresh-status",
    response_model=ApiResponse,
    summary="Refresh document status",
    description="Perform one bounded status refresh without polling.",
)
async def refresh_document(
    document_id: int, session: AsyncSession = Depends(get_session)
):
    from datetime import UTC, datetime

    item = await session.get(KnowledgeDocument, document_id)
    if item is None:
        raise NotFoundException("Knowledge document not found")
    if item.sync_status == "disabled":
        return success(document_data(item))
    item.last_checked_at = datetime.now(UTC)
    if get_settings().rag_mode == "mock":
        item.sync_status = "ready"
        item.parse_status = "ready"
        item.raw_status = "mock_ready"
    else:
        item.parse_status = "unknown"
        item.raw_status = "provider_status_pending_confirmation"
    await session.commit()
    return success(document_data(item))


def replay_data(item: RAGReplayRecord) -> dict:
    return {
        "id": item.id,
        "replay_code": item.replay_code,
        "query_fingerprint": item.query_fingerprint,
        "medicine_id": item.medicine_id,
        "task_type": item.task_type,
        "source_retrieval_id": item.source_retrieval_id,
        "is_active": item.is_active,
        "evidence_count": len(item.evidence_snapshot_json),
        "created_at": item.created_at,
    }


@router.post(
    "/rag/retrievals/{retrieval_id}/save-replay",
    response_model=ApiResponse,
    summary="Save retrieval replay",
    description="Persist a bounded evidence snapshot for explicit replay mode.",
)
async def save_replay(retrieval_id: str, session: AsyncSession = Depends(get_session)):
    retrieval = await session.scalar(
        select(RAGRetrievalRecord).where(
            RAGRetrievalRecord.retrieval_id == retrieval_id
        )
    )
    if retrieval is None or retrieval.status != "success":
        raise AppException("Only successful retrievals can be replayed")
    evidence = list(
        (
            await session.scalars(
                select(RAGEvidenceRecord).where(
                    RAGEvidenceRecord.retrieval_id == retrieval_id
                )
            )
        ).all()
    )
    if not evidence:
        raise AppException("Retrieval has no evidence")
    fingerprint = _fingerprint(RAGQuery(query=retrieval.query))
    existing = await session.scalar(
        select(RAGReplayRecord).where(
            RAGReplayRecord.query_fingerprint == fingerprint,
            RAGReplayRecord.medicine_id == retrieval.medicine_id,
            RAGReplayRecord.task_type == "identification",
        )
    )
    if existing:
        return success(replay_data(existing))
    item = RAGReplayRecord(
        replay_code=new_id("replay"),
        query_fingerprint=fingerprint,
        medicine_id=retrieval.medicine_id,
        task_type="identification",
        source_retrieval_id=retrieval_id,
        evidence_snapshot_json=[
            {
                "evidence_id": row.evidence_id,
                "document_name": row.document_name,
                "chunk_id": row.chunk_id,
                "page_number": row.page_number,
                "content": row.content_snapshot,
                "score": row.score,
                "citation": row.citation,
                "source_type": "replay",
                "data_source": "replay",
            }
            for row in evidence
        ],
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return success(replay_data(item))


@router.get(
    "/rag/replays",
    response_model=ApiResponse,
    summary="List RAG replays",
    description="List replay snapshots without raw provider responses.",
)
async def list_replays(session: AsyncSession = Depends(get_session)):
    return success(
        [
            replay_data(item)
            for item in (
                await session.scalars(
                    select(RAGReplayRecord).order_by(RAGReplayRecord.id.desc())
                )
            ).all()
        ]
    )


@router.get(
    "/rag/replays/{replay_id}",
    response_model=ApiResponse,
    summary="Get RAG replay",
    description="Get replay metadata explicitly marked as replay data.",
)
async def get_replay(replay_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(RAGReplayRecord, replay_id)
    if item is None:
        raise NotFoundException("RAG replay not found")
    return success(replay_data(item))


@router.post(
    "/rag/replays/{replay_id}/disable",
    response_model=ApiResponse,
    summary="Disable RAG replay",
    description="Disable a replay without deleting historical retrieval evidence.",
)
async def disable_replay(replay_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(RAGReplayRecord, replay_id)
    if item is None:
        raise NotFoundException("RAG replay not found")
    item.is_active = False
    await session.commit()
    return success(replay_data(item))
