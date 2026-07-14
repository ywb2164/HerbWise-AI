from __future__ import annotations

import base64
import mimetypes
from time import perf_counter
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.responses import ApiResponse, success
from app.integrations.contracts import ModelCallContext
from app.integrations.openai_compatible import (
    OpenAICompatibleLLMProvider,
    ProviderUnavailableError,
)
from app.integrations.runtime_model import (
    ModelPurpose,
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
            raise ValueError("INVALID_BASE_URL")
        return normalized

    @field_validator("model_id")
    @classmethod
    def normalize_model_id(cls, value: str) -> str:
        return value.strip()


class ModelConnectionResult(BaseModel):
    ok: bool
    reply: str


def _unconfigured_status(purpose: ModelPurpose) -> dict[str, object]:
    return {
        "purpose": purpose,
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
    raise ModelSettingsException("API_KEY_REQUIRED：请填写 API Key")


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


def _provider_error(
    exc: ProviderUnavailableError, *, vision: bool
) -> ModelSettingsException:
    messages = {
        "authentication_error": "AUTHENTICATION_FAILED：API Key 验证失败",
        "model_not_found": "MODEL_NOT_FOUND：未找到指定模型",
        "timeout_error": "MODEL_TIMEOUT：模型请求超时",
        "network_error": "PROVIDER_UNAVAILABLE：模型服务不可用",
        "configuration_error": "PROVIDER_UNAVAILABLE：模型服务配置不可用",
        "invalid_response": "MODEL_RESPONSE_EMPTY：模型未返回有效内容",
        "schema_validation_error": "MODEL_RESPONSE_EMPTY：模型未返回所需结构化内容",
        "provider_unavailable": "PROVIDER_UNAVAILABLE：模型服务暂不可用",
    }
    if vision and exc.error_code in {"invalid_response", "schema_validation_error"}:
        return ModelSettingsException(
            "MODEL_DOES_NOT_SUPPORT_VISION：该模型不支持图片输入"
        )
    return ModelSettingsException(
        messages.get(exc.error_code, "PROVIDER_UNAVAILABLE：模型服务不可用")
    )


def _form_payload(
    protocol: str, base_url: str, model_id: str, api_key: str | None
) -> ModelSettingsPayload:
    return ModelSettingsPayload(
        protocol=protocol,
        base_url=base_url,
        model_id=model_id,
        api_key=SecretStr(api_key) if api_key else None,
    )


@router.get(
    "/{purpose}",
    response_model=ApiResponse,
    summary="Get model settings",
    description="Return the current user's runtime model configuration status for the selected purpose.",
)
async def get_model_settings(
    purpose: ModelPurpose, user: User = Depends(get_current_user)
):
    config = runtime_model_registry.get_for_user(user.id, purpose)
    return success(config.public_status() if config else _unconfigured_status(purpose))


@router.put(
    "/{purpose}",
    response_model=ApiResponse,
    summary="Save model settings",
    description="Validate and save the current user's runtime model configuration for the selected purpose.",
)
async def save_model_settings(
    purpose: ModelPurpose,
    payload: ModelSettingsPayload,
    user: User = Depends(get_current_user),
):
    existing = runtime_model_registry.get_for_user(user.id, purpose)
    try:
        config = runtime_model_registry.set(
            user_id=user.id,
            learner_id=user.learner_id,
            purpose=purpose,
            protocol=payload.protocol,
            base_url=payload.base_url,
            model_name=payload.model_id,
            api_key=_api_key(payload, existing),
        )
    except ValueError as exc:
        raise ModelSettingsException(str(exc)) from exc
    return success(config.public_status())


@router.post(
    "/text/test",
    response_model=ApiResponse,
    summary="Test text model settings",
    description="Test the supplied text model configuration with a small structured response request.",
)
async def test_text_model_settings(
    payload: ModelSettingsPayload, user: User = Depends(get_current_user)
):
    existing = runtime_model_registry.get_for_user(user.id, "text")
    provider = _provider(payload, _api_key(payload, existing))
    started = perf_counter()
    try:
        result = ModelConnectionResult.model_validate(
            (
                await provider.complete_structured(
                    [
                        {
                            "role": "user",
                            "content": '请只返回 JSON：{"ok": true, "reply": "OK"}',
                        }
                    ],
                    ModelConnectionResult,
                    ModelCallContext(
                        learner_id=user.learner_id,
                        agent_code="user_text_model_test",
                        provider=f"{payload.protocol}_compatible",
                        model_name=payload.model_id,
                    ),
                )
            ).model_dump()
        )
    except ProviderUnavailableError as exc:
        raise _provider_error(exc, vision=False) from exc
    return success(
        {
            "connected": True,
            "purpose": "text",
            "model_id": payload.model_id,
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            "reply": result.reply,
        }
    )


@router.post(
    "/vision/test",
    response_model=ApiResponse,
    summary="Test vision model settings",
    description="Test the supplied vision model configuration using an uploaded image.",
)
async def test_vision_model_settings(
    file: Annotated[UploadFile, File(...)],
    protocol: Annotated[str, Form()],
    base_url: Annotated[str, Form()],
    model_id: Annotated[str, Form()],
    api_key: Annotated[str | None, Form()] = None,
    user: User = Depends(get_current_user),
):
    payload = _form_payload(protocol, base_url, model_id, api_key)
    existing = runtime_model_registry.get_for_user(user.id, "vision")
    key = _api_key(payload, existing)
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0]
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ModelSettingsException(
            "MODEL_DOES_NOT_SUPPORT_VISION：请上传 JPG、PNG 或 WebP 图片"
        )
    image = await file.read()
    if not image:
        raise ModelSettingsException("MODEL_RESPONSE_EMPTY：图片内容为空")
    if len(image) > Settings().max_upload_bytes:
        raise ModelSettingsException("MODEL_DOES_NOT_SUPPORT_VISION：图片超过大小限制")
    encoded = base64.b64encode(image).decode("ascii")
    provider = _provider(payload, key)
    started = perf_counter()
    try:
        reply = await provider.complete_text(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "这张图片中的主要对象是什么？只回答名称。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{encoded}"},
                        },
                    ],
                }
            ],
            temperature=0,
            max_tokens=64,
        )
    except ProviderUnavailableError as exc:
        raise _provider_error(exc, vision=True) from exc
    finally:
        image = b""
        encoded = ""
    if not reply.strip():
        raise ModelSettingsException("MODEL_RESPONSE_EMPTY：模型未返回图片识别结果")
    return success(
        {
            "connected": True,
            "purpose": "vision",
            "model_id": payload.model_id,
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            "reply": reply.strip(),
        }
    )


@router.delete(
    "/{purpose}",
    response_model=ApiResponse,
    summary="Clear model settings",
    description="Clear the current user's runtime model configuration for the selected purpose.",
)
async def clear_model_settings(
    purpose: ModelPurpose, user: User = Depends(get_current_user)
):
    return success({"cleared": runtime_model_registry.clear(user.id, purpose)})
