from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateLearningPlanPayload(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    daily_minutes: int = Field(default=30, ge=5, le=480)


class LearningPlanItemProposal(BaseModel):
    title: str
    reason: str
    target_dimensions: list[str]
    target_knowledge_points: list[str]
    task_type: str
    difficulty: str
    estimated_minutes: int
    resource_type: str


class LearningPlanProposal(BaseModel):
    stage: str
    summary: str
    goal: str
    daily_minutes: int
    items: list[LearningPlanItemProposal]


class ProfileAnalysis(BaseModel):
    summary: str
