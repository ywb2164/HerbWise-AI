from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MenuResponse,
    RefreshRequest,
)
from app.modules.auth.service import (
    get_current_user,
    list_menus,
    login,
    logout,
    refresh,
    user_summary,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=ApiResponse,
    summary="Log in",
    description="Authenticate and issue access and rotating refresh tokens.",
)
async def login_route(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
):
    return success(
        (await login(session, payload.username, payload.password)).model_dump(
            mode="json"
        )
    )


@router.post(
    "/refresh",
    response_model=ApiResponse,
    summary="Refresh session",
    description="Rotate a valid refresh token.",
)
async def refresh_route(
    payload: RefreshRequest, session: AsyncSession = Depends(get_session)
):
    return success(
        (await refresh(session, payload.refresh_token)).model_dump(mode="json")
    )


@router.post(
    "/logout",
    response_model=ApiResponse,
    summary="Log out",
    description="Revoke the provided refresh token.",
)
async def logout_route(
    payload: LogoutRequest, session: AsyncSession = Depends(get_session)
):
    await logout(session, payload.refresh_token)
    return success({"logged_out": True})


@router.get(
    "/me",
    response_model=ApiResponse,
    summary="Get current user",
    description="Return the authenticated user without sensitive fields.",
)
async def me(user=Depends(get_current_user)):
    return success(user_summary(user).model_dump())


@router.get(
    "/menus",
    response_model=ApiResponse,
    summary="Get accessible menus",
    description="Return menus assigned through database RBAC.",
)
async def menus(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    records = await list_menus(user, session)
    return success(
        [
            MenuResponse.model_validate(item, from_attributes=True).model_dump()
            for item in records
        ]
    )
