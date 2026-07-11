import hashlib
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select

from app.common.ids import new_id
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.exceptions import AppException, NotFoundException
from app.modules.resources.models import UploadedFile

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


async def save_upload(upload: UploadFile) -> UploadedFile:
    settings = get_settings()
    extension = ALLOWED_IMAGE_TYPES.get(upload.content_type or "")
    if extension is None:
        raise AppException("Only JPEG, PNG, and WebP images are supported")
    content = await upload.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise AppException("Uploaded file exceeds the size limit")
    file_id = new_id("file")
    relative_path = f"uploads/{file_id}{extension}"
    root = settings.upload_dir.parent
    destination = root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(destination, "wb") as target:
        await target.write(content)
    record = UploadedFile(
        file_id=file_id,
        original_name=Path(upload.filename or "upload").name,
        relative_path=relative_path,
        mime_type=upload.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    async with async_session_factory() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return record


async def get_uploaded_file(file_id: str) -> UploadedFile:
    async with async_session_factory() as session:
        record = await session.scalar(
            select(UploadedFile).where(UploadedFile.file_id == file_id)
        )
        if record is None:
            raise NotFoundException("Uploaded file not found")
        return record
