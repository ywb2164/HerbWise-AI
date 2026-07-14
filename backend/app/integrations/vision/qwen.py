from __future__ import annotations

import base64
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.integrations.contracts import (
    ModelCallContext,
    RecognitionCandidate,
    VisionProvider,
    VisionRecognitionResult,
)
from app.integrations.openai_compatible import (
    OpenAICompatibleLLMProvider,
    ProviderUnavailableError,
)
from app.integrations.runtime_model import runtime_model_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是中药材图像识别器。请根据图片判断其中最可能对应的中药材名称。

只输出一个最可能的常用中文药材名称。
不要解释，不要分析，不要列候选，不要输出英文，不要添加标点、括号、Markdown或其他文字。
无法判断时只输出：无法识别"""

USER_PROMPT = "这是什么药材？只回答一个中文药材名。"
RETRY_PROMPT = (
    "你刚才没有按照要求只返回药材名称。请只输出一个中文药材名，不要输出任何解释。"
)


def clean_medicinal_name(content: str) -> str:
    """Apply only the presentation cleanup permitted for the one-name protocol."""

    line = next((item.strip() for item in content.splitlines() if item.strip()), "")
    line = line.replace("**", "").strip()
    line = line.strip("“”\"'")
    return line.rstrip("。.,，,:：").strip()


def is_short_chinese_medicinal_name(value: str) -> bool:
    return value == "无法识别" or bool(re.fullmatch(r"[\u4e00-\u9fff]{1,20}", value))


def _resolve_vision_llm(
    context: ModelCallContext | None,
) -> tuple[str, str, OpenAICompatibleLLMProvider]:
    settings = get_settings()
    runtime = runtime_model_registry.get_for_learner(
        context.learner_id if context else None, "vision"
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
            "qwen",
            OpenAICompatibleLLMProvider(
                runtime.model_name,
                runtime_settings,
                api_key=runtime.api_key,
                protocol=runtime.protocol,
            ),
        )

    model = settings.qwen_vl_model or settings.vision_model
    if (
        not model
        or not settings.model_api_base_url
        or not settings.model_api_key.get_secret_value()
    ):
        raise ProviderUnavailableError(
            "Qwen-VL model is not configured", error_code="configuration_error"
        )
    vision_settings = Settings(
        model_api_base_url=settings.model_api_base_url,
        model_connect_timeout_seconds=settings.model_connect_timeout_seconds,
        model_read_timeout_seconds=settings.model_read_timeout_seconds,
        model_max_retries=settings.model_max_retries,
    )
    return (
        model,
        "qwen",
        OpenAICompatibleLLMProvider(
            model,
            vision_settings,
            api_key=settings.model_api_key,
        ),
    )


class QwenVisionProvider(VisionProvider):
    """Open-category primary recognizer; it is never constrained by YOLO classes."""

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
        model, provider_name, llm = _resolve_vision_llm(context)
        if settings.vision_debug:
            logger.info(
                "[QWEN_REQUEST] model=%s mime=%s bytes=%s",
                model,
                mime,
                path.stat().st_size,
            )
        raw = base64.b64encode(path.read_bytes()).decode("ascii")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{raw}"},
                    },
                ],
            },
        ]
        cleaned = "无法识别"
        for attempt in range(2):
            content = await llm.complete_text(messages, temperature=0, max_tokens=16)
            cleaned = clean_medicinal_name(content)
            if is_short_chinese_medicinal_name(cleaned):
                break
            if attempt == 0:
                messages.append({"role": "user", "content": RETRY_PROMPT})
        if not is_short_chinese_medicinal_name(cleaned):
            cleaned = "无法识别"
        candidate = RecognitionCandidate(
            herb_name=cleaned,
            raw_name=cleaned,
            confidence=0,
            in_supported_catalog=False,
            matched_by="qwen_single_name",
        )
        result = VisionRecognitionResult(
            provider=provider_name,
            model_name=model,
            file_id=context.file_id if context else None,
            candidate=candidate,
            top_candidates=[candidate],
            data_source="real",
            recognized=True,
            needs_review=cleaned == "无法识别",
        )
        if settings.vision_debug:
            logger.info(
                "[QWEN_SINGLE_NAME] name=%s retried=%s",
                cleaned,
                len(messages) > 2,
            )
        return result
