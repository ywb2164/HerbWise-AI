from enum import StrEnum

from pydantic import BaseModel, Field


class FeatureType(StrEnum):
    appearance = "appearance"
    surface = "surface"
    texture = "texture"
    section = "section"
    color = "color"
    smell = "smell"
    taste = "taste"
    processing = "processing"
    quality_control = "quality_control"
    storage = "storage"
    risk = "risk"
    training_tip = "training_tip"


class MedicineCreate(BaseModel):
    medicine_code: str = Field(min_length=1, max_length=64)
    standard_name_zh: str = Field(min_length=1, max_length=128)
    standard_name_en: str | None = Field(default=None, max_length=128)
    training_class_name: str | None = Field(default=None, max_length=128)
    latin_name: str | None = Field(default=None, max_length=255)
    source: str | None = None
    properties_flavor: str | None = Field(default=None, max_length=255)
    meridian_tropism: str | None = Field(default=None, max_length=255)
    description: str | None = None


class MedicineUpdate(BaseModel):
    standard_name_en: str | None = Field(default=None, max_length=128)
    training_class_name: str | None = Field(default=None, max_length=128)
    latin_name: str | None = Field(default=None, max_length=255)
    source: str | None = None
    properties_flavor: str | None = Field(default=None, max_length=255)
    meridian_tropism: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class FeatureCreate(BaseModel):
    feature_type: FeatureType
    feature_name: str = Field(min_length=1, max_length=128)
    feature_value: str = Field(min_length=1)
    evidence_source_id: int | None = None
    sort_order: int = Field(default=0, ge=0)


class SimilarCreate(BaseModel):
    similar_medicine_id: int
    confusion_reason: str | None = None
    distinguishing_features: dict | None = None
    risk_level: str = Field(default="low", max_length=32)
