from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.ids import new_id
from app.core.config import get_settings
from app.core.database import get_session
from app.core.exceptions import AppException, PermissionDeniedException
from app.modules.auth.models import Menu, RefreshToken, Role, User
from app.modules.auth.schemas import TokenPair, UserSummary

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationException(AppException):
    status_code = 401
    code = 1401


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def _token(
    subject: str, token_type: str, expires_in: timedelta
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + expires_in
    jti = new_id("jwt")
    payload = {
        "sub": subject,
        "jti": jti,
        "token_type": token_type,
        "iat": now,
        "exp": expires_at,
    }
    return (
        jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        ),
        jti,
        expires_at,
    )


def decode_token(token: str, expected_type: str) -> dict[str, object]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise AuthenticationException(
            "Invalid or expired authentication token"
        ) from exc
    if payload.get("token_type") != expected_type or not isinstance(
        payload.get("sub"), str
    ):
        raise AuthenticationException("Invalid authentication token")
    return payload


def user_summary(user: User) -> UserSummary:
    permissions = sorted(
        {permission.code for role in user.roles for permission in role.permissions}
    )
    if user.is_superuser:
        permissions = ["*"]
    return UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        learner_id=user.learner_id,
        roles=sorted(role.code for role in user.roles),
        permissions=permissions,
    )


async def _get_user(session: AsyncSession, username: str) -> User | None:
    stmt = (
        select(User)
        .where(User.username == username)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.roles).selectinload(Role.menus),
        )
    )
    return await session.scalar(stmt)


async def login(session: AsyncSession, username: str, password: str) -> TokenPair:
    user = await _get_user(session, username)
    if (
        user is None
        or not user.is_active
        or not verify_password(password, user.password_hash)
    ):
        raise AuthenticationException("Invalid username or password")
    settings = get_settings()
    access, _, _ = _token(
        user.username, "access", timedelta(minutes=settings.jwt_expire_minutes)
    )
    refresh, jti, expires_at = _token(
        user.username, "refresh", timedelta(days=settings.jwt_refresh_expire_days)
    )
    session.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=hash_password(refresh),
            expires_at=expires_at,
        )
    )
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(user)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_expire_minutes * 60,
        user=user_summary(user),
    )


async def refresh(session: AsyncSession, raw_token: str) -> TokenPair:
    payload = decode_token(raw_token, "refresh")
    user = await _get_user(session, str(payload["sub"]))
    record = await session.scalar(
        select(RefreshToken).where(RefreshToken.jti == str(payload["jti"]))
    )
    if (
        user is None
        or not user.is_active
        or record is None
        or record.revoked_at is not None
        or not verify_password(raw_token, record.token_hash)
    ):
        raise AuthenticationException("Invalid refresh token")
    record.revoked_at = datetime.now(UTC)
    settings = get_settings()
    access, _, _ = _token(
        user.username, "access", timedelta(minutes=settings.jwt_expire_minutes)
    )
    new_refresh, jti, expires_at = _token(
        user.username, "refresh", timedelta(days=settings.jwt_refresh_expire_days)
    )
    session.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=hash_password(new_refresh),
            expires_at=expires_at,
        )
    )
    await session.commit()
    return TokenPair(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.jwt_expire_minutes * 60,
        user=user_summary(user),
    )


async def logout(session: AsyncSession, raw_token: str) -> None:
    payload = decode_token(raw_token, "refresh")
    record = await session.scalar(
        select(RefreshToken).where(RefreshToken.jti == str(payload["jti"]))
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        await session.commit()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise AuthenticationException("Authentication required")
    payload = decode_token(credentials.credentials, "access")
    user = await _get_user(session, str(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationException("Authentication required")
    return user


def require_role(*required_roles: str):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if (
            user.is_superuser
            or required_roles
            and any(role.code in required_roles for role in user.roles)
        ):
            return user
        raise PermissionDeniedException("Insufficient role")

    return dependency


def require_permission(*required_permissions: str):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        granted = {
            permission.code for role in user.roles for permission in role.permissions
        }
        if user.is_superuser or set(required_permissions).issubset(granted):
            return user
        raise PermissionDeniedException("Insufficient permission")

    return dependency


async def list_menus(user: User, session: AsyncSession) -> list[Menu]:
    if user.is_superuser:
        return list(
            (
                await session.scalars(
                    select(Menu)
                    .where(Menu.is_enabled.is_(True), Menu.is_visible.is_(True))
                    .order_by(Menu.sort_order)
                )
            ).all()
        )
    menu_ids = {menu.id for role in user.roles for menu in role.menus}
    if not menu_ids:
        return []
    return list(
        (
            await session.scalars(
                select(Menu)
                .where(
                    Menu.id.in_(menu_ids),
                    Menu.is_enabled.is_(True),
                    Menu.is_visible.is_(True),
                )
                .order_by(Menu.sort_order)
            )
        ).all()
    )
