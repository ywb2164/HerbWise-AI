from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


RESOURCE_TYPES = frozenset(
    {
        "knowledge_card",
        "comparison_card",
        "error_explanation",
        "review_summary",
        "practice_guide",
        "quality_control_case",
        "professional_guide",
        "detailed_comparison",
    }
)
RESOURCE_DIFFICULTIES = frozenset({"basic", "intermediate", "advanced"})


class ResourceGenerationRequest(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    learning_plan_item_id: str | None = Field(default=None, max_length=64)
    task_id: str | None = Field(default=None, max_length=64)
    resource_type: str = Field(min_length=1, max_length=64)
    difficulty: str = Field(default="basic", max_length=32)
    requires_citation: bool = False
    topic: str | None = Field(default=None, min_length=1, max_length=255)
    additional_instruction: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_request(self) -> "ResourceGenerationRequest":
        if not self.learning_plan_item_id and not self.task_id and not self.topic:
            raise ValueError("A learning topic is required for free generation")
        if self.resource_type not in RESOURCE_TYPES:
            raise ValueError("resource_type is not supported")
        if self.difficulty not in RESOURCE_DIFFICULTIES:
            raise ValueError("difficulty is invalid")
        return self


class ResourceCitation(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=128)
    citation: str = Field(min_length=1, max_length=1000)


class ResourceQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(default_factory=list, max_length=8)
    answer: str = Field(min_length=1, max_length=512)
    explanation: str = Field(min_length=1, max_length=2000)


class GeneratedResourcePayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    resource_type: str
    learning_objectives: list[str] = Field(min_length=1, max_length=6)
    target_dimensions: list[str] = Field(min_length=1, max_length=6)
    target_knowledge_points: list[str] = Field(min_length=1, max_length=10)
    difficulty: str
    estimated_minutes: int = Field(ge=5, le=60)
    content_markdown: str = Field(min_length=1, max_length=20000)
    key_points: list[str] = Field(default_factory=list, max_length=12)
    questions: list[ResourceQuestion] = Field(default_factory=list, max_length=5)
    citations: list[ResourceCitation] = Field(default_factory=list, max_length=8)
    personalization_reason: str = Field(min_length=1, max_length=2000)
    safety_notice: str | None = Field(default=None, max_length=1000)


class ModelResourceReview(BaseModel):
    decision: Literal["pass", "rewrite", "reject"]
    score: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list, max_length=20)
    rewrite_required: bool = False
    rewrite_instructions: list[str] = Field(default_factory=list, max_length=12)
