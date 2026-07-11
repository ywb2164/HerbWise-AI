import pytest

from app.integrations.factory import (
    get_llm_provider,
    get_rag_provider,
    get_vision_provider,
)
from app.integrations.mock import MockLLMProvider, MockRAGProvider, MockVisionProvider


def test_factory_returns_mock_providers() -> None:
    assert isinstance(get_llm_provider(), MockLLMProvider)
    assert isinstance(get_rag_provider(), MockRAGProvider)
    assert isinstance(get_vision_provider(), MockVisionProvider)


@pytest.mark.asyncio
async def test_mock_vision_returns_three_candidates() -> None:
    result = await MockVisionProvider().recognize(None)
    assert result.candidate.herb_name == "黄芪"
    assert len(result.top_candidates) == 3
