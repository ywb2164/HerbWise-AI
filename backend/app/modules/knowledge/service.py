from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.modules.knowledge.models import (
    MedicineAlias,
    MedicineFeature,
    MedicineItem,
    SimilarMedicine,
)
from app.modules.knowledge.schemas import (
    FeatureCreate,
    FeatureUpdate,
    MedicineCreate,
    MedicineUpdate,
    SimilarCreate,
)


class MedicineConflict(AppException):
    status_code = 409
    code = 1409


def medicine_data(item: MedicineItem, matched_by: str | None = None) -> dict:
    result = {
        "id": item.id,
        "medicine_code": item.medicine_code,
        "standard_name_zh": item.standard_name_zh,
        "standard_name_en": item.standard_name_en,
        "training_class_name": item.training_class_name,
        "latin_name": item.latin_name,
        "source": item.source,
        "properties_flavor": item.properties_flavor,
        "meridian_tropism": item.meridian_tropism,
        "description": item.description,
        "is_active": item.is_active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
    if matched_by is not None:
        result["matched_by"] = matched_by
    return result


async def require_medicine(session: AsyncSession, medicine_id: int) -> MedicineItem:
    item = await session.get(MedicineItem, medicine_id)
    if item is None:
        raise NotFoundException("Medicine not found")
    return item


async def create_medicine(
    session: AsyncSession, payload: MedicineCreate
) -> MedicineItem:
    exists = await session.scalar(
        select(MedicineItem.id).where(
            or_(
                MedicineItem.medicine_code == payload.medicine_code,
                MedicineItem.standard_name_zh == payload.standard_name_zh,
            )
        )
    )
    if exists:
        raise MedicineConflict("Medicine code or standard Chinese name already exists")
    item = MedicineItem(**payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def list_medicines(
    session: AsyncSession, page: int, page_size: int, keyword: str | None
) -> dict:
    filters = []
    if keyword:
        keyword = keyword.strip()
        filters.append(
            or_(
                MedicineItem.standard_name_zh.contains(keyword),
                func.lower(MedicineItem.standard_name_en).contains(keyword.casefold()),
                MedicineItem.training_class_name.contains(keyword),
            )
        )
    total = (
        await session.scalar(
            select(func.count()).select_from(MedicineItem).where(*filters)
        )
        or 0
    )
    records = list(
        (
            await session.scalars(
                select(MedicineItem)
                .where(*filters)
                .order_by(MedicineItem.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return {
        "items": [medicine_data(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


async def update_medicine(
    session: AsyncSession, medicine_id: int, payload: MedicineUpdate
) -> MedicineItem:
    item = await require_medicine(session, medicine_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_medicine(session: AsyncSession, medicine_id: int) -> None:
    item = await require_medicine(session, medicine_id)
    feature_count = (
        await session.scalar(
            select(func.count())
            .select_from(MedicineFeature)
            .where(MedicineFeature.medicine_id == medicine_id)
        )
        or 0
    )
    if feature_count:
        raise MedicineConflict("Medicine has related features and cannot be deleted")
    await session.delete(item)
    await session.commit()


async def find_medicine_by_name(session: AsyncSession, name: str) -> dict:
    query = name.strip()
    if not query:
        raise NotFoundException("Medicine not found")
    lower = query.casefold()
    item = await session.scalar(
        select(MedicineItem).where(MedicineItem.standard_name_zh == query)
    )
    if item:
        return medicine_data(item, "standard_name_zh")
    item = await session.scalar(
        select(MedicineItem).where(func.lower(MedicineItem.standard_name_en) == lower)
    )
    if item:
        return medicine_data(item, "standard_name_en")
    item = await session.scalar(
        select(MedicineItem).where(MedicineItem.training_class_name == query)
    )
    if item:
        return medicine_data(item, "training_class_name")
    alias = await session.scalar(
        select(MedicineAlias).where(
            MedicineAlias.normalized_name == (lower if query.isascii() else query)
        )
    )
    if alias:
        return medicine_data(
            await require_medicine(session, alias.medicine_id), "alias"
        )
    raise NotFoundException("Medicine not found")


async def features(session: AsyncSession, medicine_id: int) -> list[dict]:
    await require_medicine(session, medicine_id)
    records = list(
        (
            await session.scalars(
                select(MedicineFeature)
                .where(MedicineFeature.medicine_id == medicine_id)
                .order_by(MedicineFeature.sort_order, MedicineFeature.id)
            )
        ).all()
    )
    return [
        {
            "id": item.id,
            "feature_type": item.feature_type,
            "feature_name": item.feature_name,
            "feature_value": item.feature_value,
            "evidence_source_id": item.evidence_source_id,
            "sort_order": item.sort_order,
        }
        for item in records
    ]


async def add_feature(
    session: AsyncSession, medicine_id: int, payload: FeatureCreate
) -> dict:
    await require_medicine(session, medicine_id)
    item = MedicineFeature(medicine_id=medicine_id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {
        "id": item.id,
        "feature_type": item.feature_type,
        "feature_name": item.feature_name,
        "feature_value": item.feature_value,
        "evidence_source_id": item.evidence_source_id,
        "sort_order": item.sort_order,
    }


async def update_feature(
    session: AsyncSession,
    medicine_id: int,
    feature_id: int,
    payload: FeatureUpdate,
) -> dict:
    await require_medicine(session, medicine_id)
    item = await session.scalar(
        select(MedicineFeature).where(
            MedicineFeature.id == feature_id,
            MedicineFeature.medicine_id == medicine_id,
        )
    )
    if item is None:
        raise NotFoundException("Medicine feature not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return {
        "id": item.id,
        "feature_type": item.feature_type,
        "feature_name": item.feature_name,
        "feature_value": item.feature_value,
        "evidence_source_id": item.evidence_source_id,
        "sort_order": item.sort_order,
    }


async def delete_feature(
    session: AsyncSession, medicine_id: int, feature_id: int
) -> None:
    await require_medicine(session, medicine_id)
    item = await session.scalar(
        select(MedicineFeature).where(
            MedicineFeature.id == feature_id,
            MedicineFeature.medicine_id == medicine_id,
        )
    )
    if item is None:
        raise NotFoundException("Medicine feature not found")
    await session.delete(item)
    await session.commit()


async def similar(session: AsyncSession, medicine_id: int) -> list[dict]:
    await require_medicine(session, medicine_id)
    records = list(
        (
            await session.scalars(
                select(SimilarMedicine).where(
                    SimilarMedicine.medicine_id == medicine_id
                )
            )
        ).all()
    )
    return [
        {
            "similar_medicine_id": item.similar_medicine_id,
            "confusion_reason": item.confusion_reason,
            "distinguishing_features": item.distinguishing_features_json or {},
            "risk_level": item.risk_level,
        }
        for item in records
    ]


async def add_similar(
    session: AsyncSession, medicine_id: int, payload: SimilarCreate
) -> dict:
    await require_medicine(session, medicine_id)
    await require_medicine(session, payload.similar_medicine_id)
    if medicine_id == payload.similar_medicine_id:
        raise AppException("A medicine cannot be similar to itself")
    if await session.scalar(
        select(SimilarMedicine.id).where(
            SimilarMedicine.medicine_id == medicine_id,
            SimilarMedicine.similar_medicine_id == payload.similar_medicine_id,
        )
    ):
        raise MedicineConflict("Similar medicine relation already exists")
    item = SimilarMedicine(
        medicine_id=medicine_id,
        similar_medicine_id=payload.similar_medicine_id,
        confusion_reason=payload.confusion_reason,
        distinguishing_features_json=payload.distinguishing_features,
        risk_level=payload.risk_level,
    )
    session.add(item)
    await session.commit()
    return {
        "similar_medicine_id": item.similar_medicine_id,
        "confusion_reason": item.confusion_reason,
        "distinguishing_features": item.distinguishing_features_json or {},
        "risk_level": item.risk_level,
    }
