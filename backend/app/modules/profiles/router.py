from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.profiles.schemas import (
    InitialTestSubmission,
    ProfileCreate,
    ProfileUpdate,
)
from app.modules.profiles.service import (
    create_profile,
    diagnose_profile,
    get_test_record,
    history,
    initial_questions,
    list_profiles,
    profile_data,
    profile_dimensions,
    require_profile,
    submit_initial_test,
    update_profile,
    weak_points,
)

profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])
tests_router = APIRouter(prefix="/tests", tags=["initial-tests"])


@profiles_router.post(
    "",
    response_model=ApiResponse,
    summary="Create learner profile",
    description="Create one learner profile and its six capability dimensions.",
)
async def create(payload: ProfileCreate, session: AsyncSession = Depends(get_session)):
    return success(profile_data(await create_profile(session, payload)))


@profiles_router.get(
    "",
    response_model=ApiResponse,
    summary="List learner profiles",
    description="List learner profiles with pagination and optional identity-type filtering.",
)
async def list_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity_type: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return success(await list_profiles(session, page, page_size, identity_type))


@profiles_router.get(
    "/{learner_id}",
    response_model=ApiResponse,
    summary="Get learner profile",
    description="Get one learner profile.",
)
async def get_profile(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(profile_data(await require_profile(session, learner_id)))


@profiles_router.put(
    "/{learner_id}",
    response_model=ApiResponse,
    summary="Update learner profile",
    description="Update a profile and record profile history.",
)
async def update(
    learner_id: str,
    payload: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
):
    return success(profile_data(await update_profile(session, learner_id, payload)))


@profiles_router.get(
    "/{learner_id}/dimensions",
    response_model=ApiResponse,
    summary="Get learner dimensions",
    description="Return the learner's six assessed capability dimensions.",
)
async def dimensions(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(await profile_dimensions(session, learner_id))


@profiles_router.get(
    "/{learner_id}/weak-points",
    response_model=ApiResponse,
    summary="Get learner weak points",
    description="Return traceable unresolved and resolved learner weak points.",
)
async def weak_point_list(
    learner_id: str, session: AsyncSession = Depends(get_session)
):
    return success(await weak_points(session, learner_id))


@profiles_router.get(
    "/{learner_id}/history",
    response_model=ApiResponse,
    summary="Get learner history",
    description="Return auditable learner-profile history.",
)
async def history_list(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(await history(session, learner_id))


@profiles_router.post(
    "/{learner_id}/diagnose",
    response_model=ApiResponse,
    summary="Diagnose learner",
    description="Run deterministic six-dimension profile diagnostics without an LLM.",
)
async def diagnose_route(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(await diagnose_profile(session, learner_id))


@tests_router.get(
    "/initial/questions",
    response_model=ApiResponse,
    summary="Get initial-test questions",
    description="Get active initial-assessment questions without correct answers.",
)
async def questions(session: AsyncSession = Depends(get_session)):
    return success(await initial_questions(session))


@tests_router.post(
    "/initial/submit",
    response_model=ApiResponse,
    summary="Submit initial test",
    description="Score an initial test, update dimensions and return deterministic diagnostics.",
)
async def submit(
    payload: InitialTestSubmission, session: AsyncSession = Depends(get_session)
):
    return success(await submit_initial_test(session, payload))


@tests_router.get(
    "/records/{record_id}",
    response_model=ApiResponse,
    summary="Get test record",
    description="Get a completed initial-test record.",
)
async def record(record_id: str, session: AsyncSession = Depends(get_session)):
    return success(await get_test_record(session, record_id))
