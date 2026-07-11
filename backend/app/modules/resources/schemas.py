from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.common.datetime import to_api_datetime


class UploadedFileResponse(BaseModel):
    file_id: str
    original_name: str
    relative_path: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return to_api_datetime(value)
