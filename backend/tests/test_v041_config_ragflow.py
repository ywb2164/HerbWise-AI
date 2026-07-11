from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.integrations.rag.ragflow import RAGFlowProvider
from app.integrations.openai_compatible import ProviderUnavailableError

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from scripts import config_doctor


def test_ragflow_legacy_base_url_alias_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAGFLOW_API_BASE_URL", "https://legacy.example")
    monkeypatch.delenv("RAGFLOW_BASE_URL", raising=False)
    assert Settings(_env_file=None).ragflow_base_url == "https://legacy.example"


def test_ragflow_canonical_base_url_wins_over_legacy_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAGFLOW_BASE_URL", "https://canonical.example")
    monkeypatch.setenv("RAGFLOW_API_BASE_URL", "https://legacy.example")
    assert Settings(_env_file=None).ragflow_base_url == "https://canonical.example"


def test_config_doctor_reports_effective_ragflow_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(ragflow_base_url="https://canonical.example")
    monkeypatch.setattr(config_doctor, "get_settings", lambda: settings)
    monkeypatch.setattr(config_doctor, "writable", lambda _path: (True, "writable"))
    item = next(
        check
        for check in config_doctor.checks("ragflow")
        if check.name == "ragflow_base_url"
    )
    assert item.status == "pass" and item.detail == "configured"


def _provider(
    monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport, retries: int = 1
) -> RAGFlowProvider:
    monkeypatch.setenv("RAGFLOW_API_KEY", "super-secret-key")
    original_client = httpx.AsyncClient
    import app.integrations.rag.ragflow as ragflow_module

    monkeypatch.setattr(
        ragflow_module.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    return RAGFlowProvider(
        Settings(
            ragflow_base_url="https://ragflow.invalid",
            ragflow_dataset_id="dataset_1",
            ragflow_max_retries=retries,
        )
    )


@pytest.mark.asyncio
async def test_ragflow_retries_rate_limit_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429 if calls == 1 else 200, json={"data": {}})

    body = await _provider(monkeypatch, httpx.MockTransport(handler))._request(
        "GET", "/test"
    )
    assert body == {"data": {}}
    assert calls == 2


@pytest.mark.asyncio
async def test_ragflow_authentication_error_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"message": "denied"})

    with pytest.raises(ProviderUnavailableError) as raised:
        await _provider(monkeypatch, httpx.MockTransport(handler), retries=3)._request(
            "GET", "/test"
        )
    assert raised.value.error_code == "authentication_error"
    assert calls == 1
    assert "super-secret-key" not in str(raised.value)


@pytest.mark.asyncio
async def test_ragflow_rate_limit_exhaustion_is_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"message": "rate limited"})

    with pytest.raises(ProviderUnavailableError) as raised:
        await _provider(monkeypatch, httpx.MockTransport(handler), retries=2)._request(
            "GET", "/test"
        )
    assert raised.value.error_code == "rate_limit_error"
    assert calls == 3
    assert "super-secret-key" not in str(raised.value)
