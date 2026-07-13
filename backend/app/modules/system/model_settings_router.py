from __future__ import annotations

from time import perf_counter
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.responses import ApiResponse, success
from app.integrations.contracts import ModelCallContext
from app.integrations.openai_compatible import OpenAICompatibleLLMProvider
from app.integrations.runtime_model import (
    RuntimeModelConfig,
    runtime_model_registry,
)
from app.modules.auth.models import User
from app.modules.auth.service import get_current_user

router = APIRouter(
    prefix="/model-settings",
    tags=["model-settings"],
    dependencies=[Depends(get_current_user)],
)


class ModelSettingsException(AppException):
    status_code = 422
    code = 1422


class ModelSettingsPayload(BaseModel):
    protocol: str = Field(default="openai", pattern="^(openai|anthropic)$")
    base_url: str = Field(min_length=8, max_length=512)
    model_id: str = Field(min_length=1, max_length=128)
    api_key: SecretStr | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("A valid HTTP(S) model base URL is required")
        return normalized

    @field_validator("model_id")
    @classmethod
    def normalize_model_id(cls, value: str) -> str:
        return value.strip()


class ModelConnectionResult(BaseModel):
    ok: bool
    reply: str


def _unconfigured_status() -> dict[str, object]:
    return {
        "configured": False,
        "protocol": "openai",
        "base_url": "",
        "model_id": "",
        "api_key_masked": "",
        "configured_at": None,
        "storage": "server_memory",
    }


def _api_key(payload: ModelSettingsPayload, existing: RuntimeModelConfig | None) -> str:
    if payload.api_key is not None and payload.api_key.get_secret_value():
        return payload.api_key.get_secret_value()
    if existing is not None:
        return existing.api_key.get_secret_value()
    raise ModelSettingsException("API key is required")


def _provider(
    payload: ModelSettingsPayload, api_key: str
) -> OpenAICompatibleLLMProvider:
    settings = Settings(
        model_api_base_url=payload.base_url,
        model_connect_timeout_seconds=10,
        model_read_timeout_seconds=60,
        model_max_retries=0,
    )
    return OpenAICompatibleLLMProvider(
        payload.model_id,
        settings,
        api_key=SecretStr(api_key),
        protocol=payload.protocol,
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="Get current model settings",
    description="Return model connection metadata without credential values.",
)
async def get_model_settings(user: User = Depends(get_current_user)):
    config = runtime_model_registry.get_for_user(user.id)
    return success(config.public_status() if config else _unconfigured_status())


@router.put(
    "",
    response_model=ApiResponse,
    summary="Save current model settings",
    description="Keep a user model credential in server process memory only.",
)
async def save_model_settings(
    payload: ModelSettingsPayload, user: User = Depends(get_current_user)
):
    existing = runtime_model_registry.get_for_user(user.id)
    try:
        config = runtime_model_registry.set(
            user_id=user.id,
            learner_id=user.learner_id,
            protocol=payload.protocol,
            base_url=payload.base_url,
            model_name=payload.model_id,
            api_key=_api_key(payload, existing),
        )
    except ValueError as exc:
        raise ModelSettingsException(str(exc)) from exc
    return success(config.public_status())


@router.post(
    "/test",
    response_model=ApiResponse,
    summary="Test model settings",
    description="Run a minimal structured model call without logging the credential.",
)
async def test_model_settings(
    payload: ModelSettingsPayload, user: User = Depends(get_current_user)
):
    existing = runtime_model_registry.get_for_user(user.id)
    provider = _provider(payload, _api_key(payload, existing))
    started = perf_counter()
    result = ModelConnectionResult.model_validate(
        (
            await provider.complete_structured(
                [
                    {
                        "role": "user",
                        "content": "Return a short connection acknowledgement.",
                    }
                ],
                ModelConnectionResult,
                ModelCallContext(
                    learner_id=user.learner_id,
                    agent_code="user_model_test",
                    provider=f"{payload.protocol}_compatible",
                    model_name=payload.model_id,
                ),
            )
        ).model_dump()
    )
    return success(
        {
            "connected": True,
            "protocol": payload.protocol,
            "model_id": payload.model_id,
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            "reply": result.reply,
        }
    )


@router.delete(
    "",
    response_model=ApiResponse,
    summary="Clear current model settings",
    description="Remove the in-memory credential for the current user.",
)
async def clear_model_settings(user: User = Depends(get_current_user)):
    return success({"cleared": runtime_model_registry.clear(user.id)})
