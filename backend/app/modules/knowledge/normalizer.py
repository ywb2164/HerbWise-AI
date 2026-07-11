from __future__ import annotations

import re

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import MedicineAlias, MedicineItem


class NormalizedMedicineName(BaseModel):
    matched: bool
    medicine_id: int | None = None
    standard_name_zh: str | None = None
    standard_name_en: str | None = None
    training_class_name: str | None = None
    matched_by: str | None = None
    raw_name: str
    normalized_input: str
    confidence_adjustment: float | None = None


def normalize_name(value: str) -> str:
    return re.sub(r"[\s\-_/()（）,，.。]+", "", value).casefold()


def _result(
    item: MedicineItem, raw: str, normalized: str, matched_by: str
) -> NormalizedMedicineName:
    return NormalizedMedicineName(
        matched=True,
        medicine_id=item.id,
        standard_name_zh=item.standard_name_zh,
        standard_name_en=item.standard_name_en,
        training_class_name=item.training_class_name,
        matched_by=matched_by,
        raw_name=raw,
        normalized_input=normalized,
    )


class MedicineNameNormalizer:
    """Database-backed exact normalization; deliberately no fuzzy auto-match."""

    async def normalize(
        self, session: AsyncSession, raw_name: str
    ) -> NormalizedMedicineName:
        normalized = normalize_name(raw_name)
        if not normalized:
            return NormalizedMedicineName(
                matched=False, raw_name=raw_name, normalized_input=normalized
            )

        checks = (
            (MedicineItem.training_class_name, "training_class_name"),
            (MedicineItem.standard_name_en, "standard_name_en"),
            (MedicineItem.standard_name_zh, "standard_name_zh"),
        )
        for column, matched_by in checks:
            item = await session.scalar(
                select(MedicineItem).where(func.lower(column) == raw_name.casefold())
            )
            if item is not None:
                return _result(item, raw_name, normalized, matched_by)

        alias = await session.scalar(
            select(MedicineAlias).where(MedicineAlias.normalized_name == normalized)
        )
        if alias is not None:
            item = await session.get(MedicineItem, alias.medicine_id)
            if item is not None:
                return _result(item, raw_name, normalized, "alias")

        for column, matched_by in checks:
            item = await session.scalar(
                select(MedicineItem).where(
                    func.lower(func.replace(column, " ", "")) == normalized
                )
            )
            if item is not None:
                return _result(item, raw_name, normalized, f"normalized_{matched_by}")
        return NormalizedMedicineName(
            matched=False, raw_name=raw_name, normalized_input=normalized
        )
