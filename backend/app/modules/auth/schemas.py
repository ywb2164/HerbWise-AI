from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserSummary(BaseModel):
    id: int
    username: str
    display_name: str
    learner_id: str | None
    roles: list[str]
    permissions: list[str]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class MenuResponse(BaseModel):
    code: str
    name: str
    path: str | None
    component: str | None
    icon: str | None
    sort_order: int
    menu_type: str
    permission_code: str | None
    parent_id: int | None


class TokenClaims(BaseModel):
    sub: str
    jti: str
    token_type: str
    iat: datetime
    exp: datetime
