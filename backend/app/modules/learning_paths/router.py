from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.learning_paths.service import (
    generate_learning_report,
    latest_learning_report,
    latest_path,
    path_data,
    report_data,
    require_report,
    update_path,
)

paths_router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])
reports_router = APIRouter(prefix="/reports", tags=["reports"])


@paths_router.post(
    "/update",
    response_model=ApiResponse,
    summary="Update learning path",
    description="Create a new deterministic learning-path version.",
)
async def update(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(path_data(await update_path(session, learner_id)))


@paths_router.get(
    "/{learner_id}",
    response_model=ApiResponse,
    summary="Get current learning path",
    description="Get the latest immutable learning-path version.",
)
async def get_path(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(path_data(await latest_path(session, learner_id)))


@reports_router.post(
    "/learning/{learner_id}/generate",
    response_model=ApiResponse,
    summary="Generate learning report",
    description="Persist a JSON-only mock learning report.",
)
async def generate(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(report_data(await generate_learning_report(session, learner_id)))


@reports_router.get(
    "/learning/{learner_id}",
    response_model=ApiResponse,
    summary="Get latest learning report",
    description="Get the latest JSON-only learning report.",
)
async def get_learning(learner_id: str, session: AsyncSession = Depends(get_session)):
    return success(report_data(await latest_learning_report(session, learner_id)))


@reports_router.get(
    "/{report_id}",
    response_model=ApiResponse,
    summary="Get report",
    description="Get a persisted report by identifier.",
)
async def get_report(report_id: str, session: AsyncSession = Depends(get_session)):
    return success(report_data(await require_report(session, report_id)))
