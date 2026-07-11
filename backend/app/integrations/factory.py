from app.core.config import get_settings
from app.integrations.contracts import LLMProvider, RAGProvider, VisionProvider
from app.integrations.mock import MockLLMProvider, MockRAGProvider, MockVisionProvider


def get_llm_provider() -> LLMProvider:
    if get_settings().ai_mode == "mock":
        return MockLLMProvider()
    raise NotImplementedError("Real LLM provider has not been configured")


def get_vision_provider() -> VisionProvider:
    if get_settings().yolo_mode == "mock":
        return MockVisionProvider()
    raise NotImplementedError("Real vision provider has not been configured")


def get_rag_provider() -> RAGProvider:
    if get_settings().rag_mode == "mock":
        return MockRAGProvider()
    raise NotImplementedError("Real RAG provider has not been configured")
