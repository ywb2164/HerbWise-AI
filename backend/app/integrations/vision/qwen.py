from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.integrations.contracts import (
    ModelCallContext,
    RecognitionCandidate,
    RecognitionEvidence,
    VisionProvider,
    VisionRecognitionResult,
)
from app.integrations.openai_compatible import (
    OpenAICompatibleLLMProvider,
    ProviderUnavailableError,
)
from app.integrations.runtime_model import runtime_model_registry


class QwenVisionPayload(BaseModel):
    candidate: RecognitionCandidate | None = None
    top_candidates: list[RecognitionCandidate] = Field(default_factory=list)
    character_evidence: list[RecognitionEvidence] = Field(default_factory=list)
    quality_control_evidence: list[RecognitionEvidence] = Field(default_factory=list)
    traceability_advice: list[str] = Field(default_factory=list)
    uncertainty: str | None = None


def _resolve_vision_llm(
    context: ModelCallContext | None,
) -> tuple[str, str, OpenAICompatibleLLMProvider]:
    settings = get_settings()
    runtime = runtime_model_registry.get_for_learner(
        context.learner_id if context else None
    )
    if runtime is not None:
        runtime_settings = Settings(
            model_api_base_url=runtime.base_url,
            model_connect_timeout_seconds=settings.model_connect_timeout_seconds,
            model_read_timeout_seconds=max(settings.model_read_timeout_seconds, 120.0),
            model_max_retries=settings.model_max_retries,
        )
        return (
            runtime.model_name,
            "cloud_vision",
            OpenAICompatibleLLMProvider(
                runtime.model_name,
                runtime_settings,
                api_key=runtime.api_key,
                protocol=runtime.protocol,
            ),
        )

    model = settings.qwen_vl_model or settings.vision_model
    if not model:
        raise ProviderUnavailableError(
            "Cloud vision model is not configured",
            error_code="configuration_error",
        )
    return model, "qwen", OpenAICompatibleLLMProvider(model)


class QwenVisionProvider(VisionProvider):
    provider_name = "qwen"

    async def recognize(
        self, image_path: str | None, context: ModelCallContext | None = None
    ) -> VisionRecognitionResult:
        if image_path is None:
            raise ProviderUnavailableError(
                "An uploaded image is required", error_code="unsupported_file"
            )
        path = Path(image_path)
        if not path.is_file():
            raise ProviderUnavailableError(
                "Uploaded image is unavailable", error_code="unsupported_file"
            )
        mime = mimetypes.guess_type(path.name)[0]
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            raise ProviderUnavailableError(
                "Unsupported image type", error_code="unsupported_file"
            )
        settings = get_settings()
        if path.stat().st_size > settings.max_upload_bytes:
            raise ProviderUnavailableError(
                "Uploaded image exceeds the size limit", error_code="unsupported_file"
            )
        raw = base64.b64encode(path.read_bytes()).decode("ascii")
        catalog = (context.supported_catalog if context else [])[:50]
        prompt = (
            "你是中药饮片鉴别教学助手。只能依据图像可见证据判断，不得编造不可见信息，"
            "不要提供临床治疗建议。优先从给定目录中选择；如不在目录中明确设置 in_supported_catalog=false。"
            "返回最可能候选和 Top-3、性状证据、质控证据、溯源建议、不确定性。\n目录："
            + str(catalog)
        )
        model, provider_name, llm = _resolve_vision_llm(context)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": "Return only valid JSON."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{raw}"},
                    },
                ],
            },
        ]
        parsed = await llm.complete_structured(
            messages,
            QwenVisionPayload,
            context or ModelCallContext(agent_code="vision_qwen"),
        )
        return VisionRecognitionResult(
            provider=provider_name,
            model_name=model,
            file_id=context.file_id if context else None,
            **parsed.model_dump(),
            data_source="real",
        )
