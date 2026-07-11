from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.common.datetime import to_api_datetime


class CreateTaskRequest(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    task_type: str = Field(default="full_loop", max_length=64)
    image_id: str | None = Field(default=None, max_length=64)
    image_path: str | None = Field(default=None, max_length=512)


class TaskCreatedResponse(BaseModel):
    task_id: str
    status: str


class TaskRecordResponse(BaseModel):
    task_id: str
    learner_id: str
    task_type: str
    status: str
    current_node: str | None
    progress: int
    result: dict | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @field_serializer("created_at", "started_at", "finished_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return to_api_datetime(value) if value is not None else None


class TaskEventResponse(BaseModel):
    event: str
    task_id: str
    node: str
    status: str
    progress: int
    elapsed_ms: float | None
    summary: str
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return to_api_datetime(value)
