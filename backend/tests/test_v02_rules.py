from datetime import timedelta

import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.core.exceptions import PermissionDeniedException
from app.modules.auth.models import Role, User
from app.modules.auth.service import (
    AuthenticationException,
    _token,
    decode_token,
    hash_password,
    login,
    require_role,
    verify_password,
)
from app.modules.learning_paths.rules import build_path
from app.modules.profiles.rules import DIMENSION_CODES, diagnose, score_level


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "weak"),
        (59.9, "weak"),
        (60, "basic"),
        (74.9, "basic"),
        (75, "proficient"),
        (89.9, "proficient"),
        (90, "excellent"),
        (100, "excellent"),
    ],
)
def test_profile_score_level_boundaries(score: float, expected: str) -> None:
    assert score_level(score) == expected


def test_profile_diagnosis_always_returns_six_dimensions() -> None:
    result = diagnose({"basic_knowledge": 80})

    assert set(result["dimension_scores"]) == set(DIMENSION_CODES)
    assert result["overall_level"] == "weak"
    assert "comparison_card" not in result["recommended_resource_types"]


@pytest.mark.parametrize(
    ("score", "stage"),
    [
        (0, "foundation"),
        (59.9, "foundation"),
        (60, "consolidation"),
        (84.9, "consolidation"),
        (85, "advanced"),
    ],
)
def test_learning_path_score_boundaries(score: float, stage: str) -> None:
    assert build_path(score)["current_stage"] == stage


def test_two_errors_trigger_comparison_card() -> None:
    assert (
        "comparison_card"
        in build_path(90, consecutive_errors=2)["recommended_task_types"]
    )


def test_argon2_password_hash_does_not_store_plaintext() -> None:
    encoded = hash_password("HerbWise@2026")

    assert encoded != "HerbWise@2026"
    assert verify_password("HerbWise@2026", encoded)
    assert not verify_password("wrong", encoded)


def test_access_and_refresh_tokens_have_distinct_types_and_required_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        get_settings(),
        "jwt_secret_key",
        SecretStr("unit-test-only-secret-key-at-least-32-bytes"),
    )
    access, _, _ = _token("admin", "access", timedelta(minutes=5))
    refresh, _, _ = _token("admin", "refresh", timedelta(minutes=5))

    access_claims = decode_token(access, "access")
    refresh_claims = decode_token(refresh, "refresh")
    assert {"sub", "jti", "iat", "exp", "token_type"}.issubset(access_claims)
    assert access_claims["token_type"] == "access"
    assert refresh_claims["token_type"] == "refresh"
    with pytest.raises(AuthenticationException):
        decode_token(refresh, "access")


class FakeAuthSession:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.added: list[object] = []

    async def scalar(self, _statement: object) -> User | None:
        return self.user

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        return None

    async def refresh(self, _item: object) -> None:
        return None


def make_user(role_code: str = "student", *, superuser: bool = False) -> User:
    user = User(
        id=1,
        username="student",
        password_hash=hash_password("HerbWise@2026"),
        display_name="Demo student",
        is_active=True,
        is_superuser=superuser,
    )
    role = Role(code=role_code, name=role_code, is_active=True)
    role.permissions = []
    role.menus = []
    user.roles = [role]
    return user


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_without_user_disclosure() -> None:
    session = FakeAuthSession(make_user())

    with pytest.raises(AuthenticationException, match="Invalid username or password"):
        await login(session, "student", "wrong")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_login_rejects_missing_user_with_same_message() -> None:
    session = FakeAuthSession(None)

    with pytest.raises(AuthenticationException, match="Invalid username or password"):
        await login(session, "missing", "wrong")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_student_cannot_satisfy_admin_role() -> None:
    dependency = require_role("admin")

    with pytest.raises(PermissionDeniedException):
        await dependency(make_user())


@pytest.mark.asyncio
async def test_admin_role_and_superuser_are_allowed() -> None:
    dependency = require_role("admin")

    assert (await dependency(make_user("admin"))).roles[0].code == "admin"
    assert (await dependency(make_user(superuser=True))).is_superuser
