from enum import StrEnum

from pydantic import BaseModel, Field


class ResourceType(StrEnum):
    lecture = "lecture"
    guide = "guide"
    quiz = "quiz"
    comparison_card = "comparison_card"
    review_report = "review_report"
    learning_report = "learning_report"


class ResourceStatus(StrEnum):
    generating = "generating"
    generated = "generated"
    reviewing = "reviewing"
    approved = "approved"
    needs_revision = "needs_revision"
    rejected = "rejected"
    archived = "archived"


class GenerateResourceRequest(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    medicine_name: str = Field(min_length=1, max_length=128)
    resource_type: ResourceType
    difficulty: str = Field(default="basic", max_length=32)
    task_id: str | None = Field(default=None, max_length=64)
    retrieval_id: str | None = Field(default=None, max_length=64)
    evidence_ids: list[str] = Field(default_factory=list)


class ManualDecisionRequest(BaseModel):
    status: str = Field(pattern="^(pass|needs_revision|reject|manual_review)$")
    suggestions: list[str] = Field(default_factory=list)
