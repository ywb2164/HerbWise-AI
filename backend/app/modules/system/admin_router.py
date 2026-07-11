from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import AppException, NotFoundException
from app.core.responses import ApiResponse, success
from app.modules.auth.models import Menu, Role, User
from app.modules.auth.service import require_role
from app.modules.resources.business_models import PromptTemplate
from app.modules.system.models import AgentConfig, ModelConfig, SystemConfig, TestCase
from app.modules.tasks.models import AgentLog

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))]
)


class AdminWritePayload(BaseModel):
    data: dict[str, object]


class AdminConflictException(AppException):
    status_code = 409
    code = 1409


_WRITABLE = {
    "roles": Role,
    "menus": Menu,
    "model-configs": ModelConfig,
    "agent-configs": AgentConfig,
    "prompt-templates": PromptTemplate,
    "system-configs": SystemConfig,
    "test-cases": TestCase,
}


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


@router.post(
    "/{target}",
    response_model=ApiResponse,
    summary="Create admin record",
    description="Create an allow-listed configuration record; credential values are not accepted.",
)
async def create_record(
    target: str,
    payload: AdminWritePayload,
    session: AsyncSession = Depends(get_session),
):
    model = _WRITABLE.get(target)
    if model is None:
        raise NotFoundException("Unsupported admin resource")
    data = dict(payload.data)
    data.pop("password_hash", None)
    data.pop("credential", None)
    item = model(**data)
    session.add(item)
    if target == "agent-configs":
        session.add(
            AgentLog(
                task_id="admin_config",
                node_name="admin:create:agent-configs",
                provider="system",
                input_summary="redacted configuration payload",
                output_summary="agent configuration created",
                status="success",
            )
        )
    await session.commit()
    await session.refresh(item)
    return success(
        {
            column.name: getattr(item, column.name)
            for column in item.__table__.columns
            if column.name not in {"password_hash"}
        }
    )


@router.put(
    "/{target}/{record_id}",
    response_model=ApiResponse,
    summary="Update admin record",
    description="Update an allow-listed configuration record.",
)
async def update_record(
    target: str,
    record_id: int,
    payload: AdminWritePayload,
    session: AsyncSession = Depends(get_session),
):
    model = _WRITABLE.get(target)
    if model is None:
        raise NotFoundException("Unsupported admin resource")
    item = await session.get(model, record_id)
    if item is None:
        raise NotFoundException("Admin record not found")
    for key, value in payload.data.items():
        if key not in {"id", "password_hash", "credential"} and hasattr(item, key):
            setattr(item, key, value)
    if target == "agent-configs":
        session.add(
            AgentLog(
                task_id="admin_config",
                node_name="admin:update:agent-configs",
                provider="system",
                input_summary="redacted configuration payload",
                output_summary=f"agent configuration {record_id} updated",
                status="success",
            )
        )
    await session.commit()
    await session.refresh(item)
    return success(
        {
            column.name: getattr(item, column.name)
            for column in item.__table__.columns
            if column.name not in {"password_hash"}
        }
    )


@router.delete(
    "/{target}/{record_id}",
    response_model=ApiResponse,
    summary="Delete admin record",
    description="Delete an allow-listed configuration record when it is not referenced.",
)
async def delete_record(
    target: str, record_id: int, session: AsyncSession = Depends(get_session)
):
    model = _WRITABLE.get(target)
    if model is None:
        raise NotFoundException("Unsupported admin resource")
    item = await session.get(model, record_id)
    if item is None:
        raise NotFoundException("Admin record not found")
    if target == "model-configs" and await session.scalar(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.model_config_id == record_id)
    ):
        raise AdminConflictException("Model configuration is referenced by an agent")
    if target == "prompt-templates" and await session.scalar(
        select(func.count())
        .select_from(AgentConfig)
        .where(AgentConfig.prompt_template_id == record_id)
    ):
        raise AdminConflictException("Prompt template is referenced by an agent")
    await session.delete(item)
    await session.commit()
    return success({"deleted": True})
