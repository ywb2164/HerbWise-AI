from app.core.config import get_settings
from app.integrations.contracts import (
    LLMProvider,
    LocalVisionProvider,
    RAGProvider,
    VisionProvider,
)
from app.integrations.mock import MockLLMProvider, MockRAGProvider, MockVisionProvider
from app.integrations.rag.ragflow import RAGFlowProvider
from app.integrations.openai_compatible import OpenAICompatibleLLMProvider
from app.integrations.runtime_model import runtime_model_registry
from app.integrations.vision.local import UltralyticsLocalVisionProvider
from app.integrations.vision.qwen import QwenVisionProvider
from app.modules.system.models import ModelConfig

RUNTIME_MODEL_READ_TIMEOUT_SECONDS = 120.0


def get_llm_provider(
    model_config: ModelConfig | None = None, learner_id: str | None = None
) -> LLMProvider:
    settings = get_settings()
    runtime_config = runtime_model_registry.get_for_learner(learner_id)
    if runtime_config is not None:
        from app.core.config import Settings

        configured = Settings(
            model_api_base_url=runtime_config.base_url,
            model_connect_timeout_seconds=settings.model_connect_timeout_seconds,
            model_read_timeout_seconds=max(
                settings.model_read_timeout_seconds,
                RUNTIME_MODEL_READ_TIMEOUT_SECONDS,
            ),
            model_max_retries=settings.model_max_retries,
        )
        return OpenAICompatibleLLMProvider(
            runtime_config.model_name,
            configured,
            api_key=runtime_config.api_key,
            protocol=runtime_config.protocol,
        )
    if model_config is not None:
        from app.core.config import Settings

        configured = Settings(
            model_api_base_url=model_config.base_url or "",
            model_connect_timeout_seconds=model_config.timeout_seconds,
            model_read_timeout_seconds=model_config.timeout_seconds,
            model_max_retries=model_config.max_retries,
        )
        return OpenAICompatibleLLMProvider(
            model_config.model_name,
            configured,
            model_config.credential_reference,
            protocol="anthropic"
            if model_config.provider.startswith("anthropic")
            else "openai",
        )
    if settings.llm_mode == "mock" and settings.ai_mode == "mock":
        return MockLLMProvider()
    model = settings.generation_model or settings.text_model
    return OpenAICompatibleLLMProvider(model)


def get_vision_provider() -> VisionProvider:
    settings = get_settings()
    if settings.effective_vision_mode() == "mock":
        return MockVisionProvider()
    if settings.effective_vision_mode() == "qwen":
        return QwenVisionProvider()
    raise ValueError("Use the local or hybrid vision factory for this vision mode")


def get_qwen_vision_provider() -> VisionProvider:
    return QwenVisionProvider()


def get_local_vision_provider() -> LocalVisionProvider:
    return UltralyticsLocalVisionProvider()


def get_rag_provider() -> RAGProvider:
    if get_settings().rag_mode in {"mock", "replay"}:
        return MockRAGProvider()
    return RAGFlowProvider()
