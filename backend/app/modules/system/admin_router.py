from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.config import Settings
from app.core.exceptions import AppException, NotFoundException
from app.core.responses import ApiResponse, success
from app.modules.auth.models import Menu, Role, User
from app.modules.auth.service import get_current_user, hash_password, require_role
from app.modules.resources.business_models import PromptTemplate
from app.modules.system.models import AgentConfig, ModelConfig, SystemConfig, TestCase
from app.modules.tasks.models import AgentLog, TaskRecord
from app.integrations.contracts import ModelCallContext
from app.integrations.openai_compatible import OpenAICompatibleLLMProvider

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))]
)


class AdminWritePayload(BaseModel):
    data: dict[str, object]


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    learner_id: str | None = Field(default=None, max_length=64)
    is_active: bool = True
    is_superuser: bool = False
    role_codes: list[str] = Field(default_factory=list)


class AdminUserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=256)
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    learner_id: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None
    is_superuser: bool | None = None
    role_codes: list[str] | None = None


class AdminConflictException(AppException):
    status_code = 409
    code = 1409


class ModelConfigTestPayload(BaseModel):
    message: str = Field(default="ping", min_length=1, max_length=64)


class ModelConfigTestResult(BaseModel):
    ok: bool
    reply: str


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
    descending: bool = False,
) -> dict:
    total = await session.scalar(select(func.count()).select_from(model)) or 0
    records = list(
        (
            await session.scalars(
                select(model)
                .order_by(model.id.desc() if descending else model.id)
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
    total = await session.scalar(select(func.count()).select_from(User)) or 0
    records = list(
        (
            await session.scalars(
                select(User)
                .order_by(User.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return success(
        {
            "items": [_user_data(user) for user in records],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }
    )


def _user_data(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "learner_id": user.learner_id,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": sorted(role.code for role in user.roles),
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


async def _roles_by_code(session: AsyncSession, role_codes: list[str]) -> list[Role]:
    if not role_codes:
        return []
    roles = list(
        (
            await session.scalars(select(Role).where(Role.code.in_(set(role_codes))))
        ).all()
    )
    if len(roles) != len(set(role_codes)):
        raise NotFoundException("One or more roles do not exist")
    return roles


@router.post(
    "/users",
    response_model=ApiResponse,
    summary="Create user",
    description="Create a user with an Argon2 password hash and database roles.",
)
async def create_user(
    payload: AdminUserCreate, session: AsyncSession = Depends(get_session)
):
    if await session.scalar(select(User.id).where(User.username == payload.username)):
        raise AdminConflictException("Username already exists")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        email=payload.email,
        learner_id=payload.learner_id,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        roles=await _roles_by_code(session, payload.role_codes),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return success(_user_data(user))


@router.put(
    "/users/{user_id}",
    response_model=ApiResponse,
    summary="Update user",
    description="Update user fields, password hash, or assigned roles.",
)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundException("User not found")
    updates = payload.model_dump(exclude_unset=True, exclude={"password", "role_codes"})
    for key, value in updates.items():
        setattr(user, key, value)
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role_codes is not None:
        user.roles = await _roles_by_code(session, payload.role_codes)
    await session.commit()
    await session.refresh(user)
    return success(_user_data(user))


@router.delete(
    "/users/{user_id}",
    response_model=ApiResponse,
    summary="Delete user",
    description="Delete a user and cascading role/token associations.",
)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise AdminConflictException("The current administrator cannot be deleted")
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundException("User not found")
    await session.delete(user)
    await session.commit()
    return success({"deleted": True})


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


@router.post(
    "/model-configs/{config_id}/test",
    response_model=ApiResponse,
    summary="Test a model configuration",
    description="Perform one minimal administrator-triggered call without returning credentials or raw provider output.",
)
async def test_model_config(
    config_id: int,
    payload: ModelConfigTestPayload,
    session: AsyncSession = Depends(get_session),
):
    config = await session.get(ModelConfig, config_id)
    if config is None or not config.is_active:
        raise NotFoundException("Active model configuration not found")
    settings = Settings(
        model_api_base_url=config.base_url or "",
        model_connect_timeout_seconds=config.timeout_seconds,
        model_read_timeout_seconds=config.timeout_seconds,
        model_max_retries=config.max_retries,
    )
    provider = OpenAICompatibleLLMProvider(
        config.model_name,
        settings,
        config.credential_reference,
        protocol="anthropic" if config.provider.startswith("anthropic") else "openai",
    )
    started = __import__("time").perf_counter()
    result = await provider.complete_structured(
        [{"role": "user", "content": payload.message}],
        ModelConfigTestResult,
        ModelCallContext(
            agent_code="admin_model_test",
            provider=config.provider,
            model_name=config.model_name,
        ),
    )
    elapsed = round((__import__("time").perf_counter() - started) * 1000, 2)
    return success(
        {
            "connected": True,
            "model_name": config.model_name,
            "elapsed_ms": elapsed,
            "result": result.model_dump(),
        }
    )


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


@router.get(
    "/task-records",
    response_model=ApiResponse,
    summary="List agent tasks",
    description="List persisted agent task execution records.",
)
async def task_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, TaskRecord, page, page_size, descending=True))


@router.get(
    "/agent-logs",
    response_model=ApiResponse,
    summary="List agent logs",
    description="List redacted per-node model and agent execution logs.",
)
async def agent_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return success(await _page(session, AgentLog, page, page_size, descending=True))


@router.post(
    "/{target}",
    response_model=ApiResponse,
    summary="Create admin record",
    description="Create an allow-listed configuration record; credential values are not accepted.",
    include_in_schema=False,
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
    include_in_schema=False,
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
    include_in_schema=False,
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


def _register_concrete_crud_routes() -> None:
    for target in _WRITABLE:
        if target == "users":
            continue

        def create_factory(resource: str):
            async def concrete_create(
                payload: AdminWritePayload,
                session: AsyncSession = Depends(get_session),
            ):
                return await create_record(resource, payload, session)

            return concrete_create

        def update_factory(resource: str):
            async def concrete_update(
                record_id: int,
                payload: AdminWritePayload,
                session: AsyncSession = Depends(get_session),
            ):
                return await update_record(resource, record_id, payload, session)

            return concrete_update

        def delete_factory(resource: str):
            async def concrete_delete(
                record_id: int,
                session: AsyncSession = Depends(get_session),
            ):
                return await delete_record(resource, record_id, session)

            return concrete_delete

        label = target.replace("-", " ")
        router.add_api_route(
            f"/{target}",
            create_factory(target),
            methods=["POST"],
            response_model=ApiResponse,
            summary=f"Create {label}",
            description=f"Create one {label} administration record.",
            operation_id=f"admin_create_{target.replace('-', '_')}",
        )
        router.add_api_route(
            f"/{target}/{{record_id}}",
            update_factory(target),
            methods=["PUT"],
            response_model=ApiResponse,
            summary=f"Update {label}",
            description=f"Update one {label} administration record.",
            operation_id=f"admin_update_{target.replace('-', '_')}",
        )
        router.add_api_route(
            f"/{target}/{{record_id}}",
            delete_factory(target),
            methods=["DELETE"],
            response_model=ApiResponse,
            summary=f"Delete {label}",
            description=f"Delete one unreferenced {label} administration record.",
            operation_id=f"admin_delete_{target.replace('-', '_')}",
        )


_register_concrete_crud_routes()
