from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.models import Menu, Role, User
from app.modules.auth.service import require_role
from app.modules.resources.business_models import PromptTemplate
from app.modules.system.models import AgentConfig, ModelConfig, SystemConfig, TestCase

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))]
)


async def _page(
    session: AsyncSession,
    model,
    page: int,
    page_size: int,
    hidden: set[str] | None = None,
) -> dict:
    total = await session.scalar(select(func.count()).select_from(model)) or 0
    records = list(
        (
            await session.scalars(
                select(model)
                .order_by(model.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    hidden = hidden or set()
    return {
        "items": [
            {
                column.name: getattr(item, column.name)
                for column in item.__table__.columns
                if column.name not in hidden
            }
            for item in records
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get(
    "/users",
    response_model=ApiResponse,
    summary="List users",
    description="List users without password hashes.",
)
async def users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, User, page, page_size, {"password_hash"}))


@router.get(
    "/roles",
    response_model=ApiResponse,
    summary="List roles",
    description="List roles for administration.",
)
async def roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, Role, page, page_size))


@router.get(
    "/menus",
    response_model=ApiResponse,
    summary="List menus",
    description="List menus for administration.",
)
async def menus(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, Menu, page, page_size))


@router.get(
    "/model-configs",
    response_model=ApiResponse,
    summary="List model configurations",
    description="List model configuration references without credentials.",
)
async def model_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, ModelConfig, page, page_size))


@router.get(
    "/agent-configs",
    response_model=ApiResponse,
    summary="List agent configurations",
    description="List database-backed agent configuration.",
)
async def agent_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, AgentConfig, page, page_size))


@router.get(
    "/prompt-templates",
    response_model=ApiResponse,
    summary="List prompt templates",
    description="List versioned prompt templates.",
)
async def prompts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, PromptTemplate, page, page_size))


@router.get(
    "/system-configs",
    response_model=ApiResponse,
    summary="List system configurations",
    description="List system configuration values.",
)
async def system_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, SystemConfig, page, page_size))


@router.get(
    "/test-cases",
    response_model=ApiResponse,
    summary="List test cases",
    description="List mock evaluation cases.",
)
async def test_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, TestCase, page, page_size))
