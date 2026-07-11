from fastapi import APIRouter, File, UploadFile

from app.modules.resources.models import UploadedFile
from app.modules.resources.schemas import UploadedFileResponse
from app.modules.resources.service import get_uploaded_file, save_upload

router = APIRouter(prefix="/files", tags=["files"])


def serialize(record: UploadedFile) -> UploadedFileResponse:
    return UploadedFileResponse(
        file_id=record.file_id,
        original_name=record.original_name,
        relative_path=record.relative_path,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        created_at=record.created_at,
    )


@router.post("/upload", response_model=UploadedFileResponse, status_code=201)
async def upload_file(file: UploadFile = File(...)) -> UploadedFileResponse:
    return serialize(await save_upload(file))


@router.get("/{file_id}", response_model=UploadedFileResponse)
async def get_file(file_id: str) -> UploadedFileResponse:
    return serialize(await get_uploaded_file(file_id))
