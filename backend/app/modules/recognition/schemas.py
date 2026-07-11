from pydantic import BaseModel, Field


class VisionRecognizeRequest(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    file_id: str = Field(min_length=1, max_length=64)
    task_id: str | None = Field(default=None, max_length=64)
    vision_mode: str | None = Field(default=None, pattern="^(mock|qwen|local|hybrid)$")
