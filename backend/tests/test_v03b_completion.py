import pytest

from app.integrations.contracts import RAGQuery
from app.integrations.mock import MockRAGProvider
from app.modules.knowledge.rag_service import _rank, _truncate


@pytest.mark.asyncio
async def test_mock_rag_returns_citations() -> None:
    result = await MockRAGProvider().retrieve_detailed(RAGQuery(query="黄芪 性状"))
    assert result.success and all(item.citation for item in result.evidences)


@pytest.mark.asyncio
async def test_mock_rag_health() -> None:
    assert (await MockRAGProvider().health_check())["reachable"] is True


@pytest.mark.parametrize("top_k", [1, 2, 3])
@pytest.mark.asyncio
async def test_mock_rag_honors_top_k(top_k: int) -> None:
    assert (
        len(
            (
                await MockRAGProvider().retrieve_detailed(
                    RAGQuery(query="甘草", top_k=top_k)
                )
            ).evidences
        )
        == top_k
    )


@pytest.mark.asyncio
async def test_replay_contract_is_serializable() -> None:
    result = await MockRAGProvider().retrieve_detailed(RAGQuery(query="党参"))
    assert result.model_dump(mode="json")["data_source"] == "mock"


def test_rank_is_stable() -> None:
    import asyncio

    evidence = asyncio.run(
        MockRAGProvider().retrieve_detailed(RAGQuery(query="黄芪"))
    ).evidences
    assert [item.rank for item in _rank(evidence)] == [1, 2, 3]


def test_truncate_limits_items() -> None:
    import asyncio

    evidence = asyncio.run(
        MockRAGProvider().retrieve_detailed(RAGQuery(query="黄芪"))
    ).evidences
    assert len(_truncate(evidence, 1, 1000)) == 1
