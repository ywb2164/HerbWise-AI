from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from app.integrations.factory import get_llm_provider
from app.integrations.openai_compatible import OpenAICompatibleLLMProvider
from app.integrations.runtime_model import RuntimeModelRegistry, runtime_model_registry
from app.integrations.vision.qwen import _resolve_vision_llm
from app.main import create_app
from app.modules.auth.service import get_current_user


def test_registry_keeps_purposes_and_users_isolated() -> None:
    registry = RuntimeModelRegistry()
    vision = registry.set(
        user_id=1,
        learner_id="learner_1",
        purpose="vision",
        protocol="openai",
        base_url="https://vision.example/v1",
        model_name="vision",
        api_key="vision-key",
    )
    text = registry.set(
        user_id=1,
        learner_id="learner_1",
        purpose="text",
        protocol="anthropic",
        base_url="https://text.example/v1",
        model_name="text",
        api_key="text-key",
    )
    registry.set(
        user_id=2,
        learner_id="learner_2",
        purpose="vision",
        protocol="openai",
        base_url="https://other.example/v1",
        model_name="other",
        api_key="other-key",
    )

    assert registry.get_for_user(1, "vision") is vision
    assert registry.get_for_user(1, "text") is text
    assert registry.get_for_user(2, "text") is None
    assert registry.clear(1, "text") is True
    assert registry.get_for_user(1, "vision") is vision
    registry.clear_all()
    assert registry.get_for_user(1, "vision") is None


def test_providers_read_only_their_assigned_purpose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_model_registry.clear_all()
    runtime_model_registry.set(
        user_id=1,
        learner_id="learner_1",
        purpose="vision",
        protocol="openai",
        base_url="https://vision.example/v1",
        model_name="vision-only",
        api_key="vision-key",
    )
    runtime_model_registry.set(
        user_id=1,
        learner_id="learner_1",
        purpose="text",
        protocol="openai",
        base_url="https://text.example/v1",
        model_name="text-only",
        api_key="text-key",
    )
    settings = SimpleNamespace(
        model_connect_timeout_seconds=10,
        model_read_timeout_seconds=30,
        model_max_retries=0,
        qwen_vl_model="",
        vision_model="",
    )
    monkeypatch.setattr("app.integrations.factory.get_settings", lambda: settings)
    monkeypatch.setattr("app.integrations.vision.qwen.get_settings", lambda: settings)
    try:
        text_provider = get_llm_provider(learner_id="learner_1")
        model, _, vision_provider = _resolve_vision_llm(
            SimpleNamespace(learner_id="learner_1")
        )
        assert isinstance(text_provider, OpenAICompatibleLLMProvider)
        assert text_provider.model_name == "text-only"
        assert model == "vision-only"
        assert vision_provider.model_name == "vision-only"
    finally:
        runtime_model_registry.clear_all()


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    async def current_user() -> object:
        return SimpleNamespace(id=101, learner_id="learner_101")

    app.dependency_overrides[get_current_user] = current_user
    with TestClient(app) as test_client:
        yield test_client
    runtime_model_registry.clear_all()


def test_model_settings_api_is_purpose_scoped_and_redacts_key(
    client: TestClient,
) -> None:
    vision = client.put(
        "/api/model-settings/vision",
        json={
            "protocol": "openai",
            "base_url": "https://vision.example/v1",
            "model_id": "vision-model",
            "api_key": "vision-secret-1234",
        },
    )
    text = client.put(
        "/api/model-settings/text",
        json={
            "protocol": "openai",
            "base_url": "https://text.example/v1",
            "model_id": "text-model",
            "api_key": "text-secret-5678",
        },
    )
    saved_vision = vision.json()["data"]
    saved_text = text.json()["data"]

    assert vision.status_code == 200 and text.status_code == 200
    assert saved_vision["purpose"] == "vision"
    assert saved_text["purpose"] == "text"
    assert saved_vision["model_id"] == "vision-model"
    assert saved_text["model_id"] == "text-model"
    assert "vision-secret-1234" not in vision.text
    assert "text-secret-5678" not in text.text
    assert client.delete("/api/model-settings/text").json()["data"]["cleared"] is True
    assert client.get("/api/model-settings/vision").json()["data"]["configured"] is True


@pytest.mark.asyncio
async def test_vision_test_sends_multimodal_message(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    captured: dict[str, object] = {}

    async def fake_complete_text(self, messages, *, temperature, max_tokens):
        captured["messages"] = messages
        return "蜂房"

    monkeypatch.setattr(
        OpenAICompatibleLLMProvider, "complete_text", fake_complete_text
    )
    response = client.post(
        "/api/model-settings/vision/test",
        data={
            "protocol": "openai",
            "base_url": "https://vision.example/v1",
            "model_id": "vision-model",
            "api_key": "vision-key",
        },
        files={"file": ("sample.png", b"png", "image/png")},
    )

    assert response.status_code == 200
    message = captured["messages"][0]
    assert message["content"][1]["type"] == "image_url"
    assert response.json()["data"]["purpose"] == "vision"
