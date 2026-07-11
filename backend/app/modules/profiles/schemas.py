from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.profiles.rules import DIMENSION_CODES


class DimensionCode(StrEnum):
    basic_knowledge = "basic_knowledge"
    character_identification = "character_identification"
    similar_medicine = "similar_medicine"
    pharmacopoeia_rules = "pharmacopoeia_rules"
    clinical_quality_control = "clinical_quality_control"
    practical_review = "practical_review"


class ProfileCreate(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    identity_type: str = Field(min_length=1, max_length=32)
    user_id: int | None = None
    education_background: str | None = Field(default=None, max_length=255)
    professional_background: str | None = Field(default=None, max_length=255)
    learning_goal: str | None = None
    learning_preference: str | None = Field(default=None, max_length=64)
    dimensions: dict[DimensionCode, float] | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    identity_type: str | None = Field(default=None, min_length=1, max_length=32)
    education_background: str | None = Field(default=None, max_length=255)
    professional_background: str | None = Field(default=None, max_length=255)
    learning_goal: str | None = None
    learning_preference: str | None = Field(default=None, max_length=64)
    dimensions: dict[DimensionCode, float] | None = None


class TestAnswerInput(BaseModel):
    question_id: int
    answer: str | int | float | bool


class InitialTestSubmission(BaseModel):
    learner_id: str = Field(min_length=1, max_length=64)
    answers: list[TestAnswerInput] = Field(min_length=1)


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


def empty_dimension_scores() -> dict[str, float]:
    return dict.fromkeys(DIMENSION_CODES, 0.0)
