from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.service import get_current_user, require_role
from app.modules.knowledge.schemas import (
    FeatureCreate,
    FeatureUpdate,
    MedicineCreate,
    MedicineUpdate,
    SimilarCreate,
)
from app.modules.knowledge.service import (
    add_feature,
    add_similar,
    create_medicine,
    delete_feature,
    delete_medicine,
    features,
    find_medicine_by_name,
    list_medicines,
    medicine_data,
    require_medicine,
    similar,
    update_medicine,
    update_feature,
)

router = APIRouter(
    prefix="/medicines",
    tags=["medicines"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=ApiResponse,
    summary="Create medicine",
    description="Create a structured demo medicine record.",
)
async def create(
    payload: MedicineCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    return success(medicine_data(await create_medicine(session, payload)))


@router.get(
    "",
    response_model=ApiResponse,
    summary="List medicines",
    description="List structured medicine records with pagination.",
)
async def list_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return success(await list_medicines(session, page, page_size, keyword))


@router.get(
    "/by-name/{name}",
    response_model=ApiResponse,
    summary="Find medicine by name",
    description="Match Chinese, English, training class name, or alias.",
)
async def by_name(name: str, session: AsyncSession = Depends(get_session)):
    return success(await find_medicine_by_name(session, name))


@router.get(
    "/{medicine_id}",
    response_model=ApiResponse,
    summary="Get medicine",
    description="Get a structured medicine record.",
)
async def get_route(medicine_id: int, session: AsyncSession = Depends(get_session)):
    return success(medicine_data(await require_medicine(session, medicine_id)))


@router.put(
    "/{medicine_id}",
    response_model=ApiResponse,
    summary="Update medicine",
    description="Update a structured medicine record.",
)
async def update(
    medicine_id: int,
    payload: MedicineUpdate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    return success(medicine_data(await update_medicine(session, medicine_id, payload)))


@router.delete(
    "/{medicine_id}",
    response_model=ApiResponse,
    summary="Delete medicine",
    description="Delete a medicine only when it has no related feature records.",
)
async def delete(
    medicine_id: int,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    await delete_medicine(session, medicine_id)
    return success({"deleted": True})


@router.get(
    "/{medicine_id}/features",
    response_model=ApiResponse,
    summary="List medicine features",
    description="List structured medicine features.",
)
async def feature_list(medicine_id: int, session: AsyncSession = Depends(get_session)):
    return success(await features(session, medicine_id))


@router.post(
    "/{medicine_id}/features",
    response_model=ApiResponse,
    summary="Add medicine feature",
    description="Add a typed structured medicine feature.",
)
async def feature_add(
    medicine_id: int,
    payload: FeatureCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    return success(await add_feature(session, medicine_id, payload))


@router.put(
    "/{medicine_id}/features/{feature_id}",
    response_model=ApiResponse,
    summary="Update medicine feature",
    description="Update one typed structured medicine feature.",
)
async def feature_update(
    medicine_id: int,
    feature_id: int,
    payload: FeatureUpdate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    return success(await update_feature(session, medicine_id, feature_id, payload))


@router.delete(
    "/{medicine_id}/features/{feature_id}",
    response_model=ApiResponse,
    summary="Delete medicine feature",
    description="Delete a single structured medicine feature.",
)
async def feature_delete(
    medicine_id: int,
    feature_id: int,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    await delete_feature(session, medicine_id, feature_id)
    return success({"deleted": True})


@router.get(
    "/{medicine_id}/similar",
    response_model=ApiResponse,
    summary="List similar medicines",
    description="List configured look-alike medicine relations.",
)
async def similar_list(medicine_id: int, session: AsyncSession = Depends(get_session)):
    return success(await similar(session, medicine_id))


@router.post(
    "/{medicine_id}/similar",
    response_model=ApiResponse,
    summary="Add similar medicine",
    description="Add a medicine comparison relation.",
)
async def similar_add(
    medicine_id: int,
    payload: SimilarCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(
        require_role("admin", "teacher", "clinical_pharmacist", "quality_inspector")
    ),
):
    return success(await add_similar(session, medicine_id, payload))
