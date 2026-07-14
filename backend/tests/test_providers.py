from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.integrations.contracts import ModelCallContext
from app.integrations.factory import (
    get_llm_provider,
    get_rag_provider,
    get_vision_provider,
)
from app.integrations.mock import MockLLMProvider, MockRAGProvider, MockVisionProvider
from app.integrations.openai_compatible import OpenAICompatibleLLMProvider
from app.integrations.runtime_model import RuntimeModelRegistry
from app.integrations.runtime_model import runtime_model_registry
from app.integrations.vision.qwen import QwenVisionProvider


def test_factory_returns_mock_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.integrations.factory as factory

    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: SimpleNamespace(
            ai_mode="mock",
            llm_mode="mock",
            rag_mode="mock",
            generation_model="",
            text_model="",
            effective_vision_mode=lambda: "mock",
        ),
    )
    assert isinstance(get_llm_provider(), MockLLMProvider)
    assert isinstance(get_rag_provider(), MockRAGProvider)
    assert isinstance(get_vision_provider(), MockVisionProvider)


@pytest.mark.asyncio
async def test_mock_vision_returns_three_candidates() -> None:
    result = await MockVisionProvider().recognize(None)
    assert result.candidate.herb_name == "黄芪"
    assert len(result.top_candidates) == 3


def test_runtime_model_registry_isolates_and_redacts_credentials() -> None:
    registry = RuntimeModelRegistry()
    config = registry.set(
        user_id=7,
        learner_id="stu_007",
        protocol="openai",
        base_url="https://models.example.test/v2/",
        model_name="test-model",
        api_key="test-key-1234",
    )

    assert registry.get_for_user(7) is config
    assert registry.get_for_learner("stu_007") is config
    assert config.public_status()["api_key_masked"] == "****1234"
    assert "test-key-1234" not in repr(config)
    assert registry.clear(7) is True
    assert registry.get_for_learner("stu_007") is None


def test_runtime_model_provider_allows_slow_structured_calls() -> None:
    runtime_model_registry.set(
        user_id=8,
        learner_id="stu_008",
        protocol="openai",
        base_url="https://models.example.test/v2",
        model_name="test-model",
        api_key="test-key",
    )
    try:
        provider = get_llm_provider(learner_id="stu_008")
        assert isinstance(provider, OpenAICompatibleLLMProvider)
        assert provider.settings.model_read_timeout_seconds == 120
    finally:
        runtime_model_registry.clear(8)


def test_anthropic_response_is_normalized_to_chat_completion() -> None:
    provider = OpenAICompatibleLLMProvider(
        "test-model",
        api_key=SecretStr("test-key"),
        protocol="anthropic",
    )

    result = provider._normalize_anthropic_response(
        {
            "content": [
                {"type": "thinking", "thinking": "hidden"},
                {"type": "text", "text": '{"ok": true}'},
            ]
        }
    )

    assert result["choices"][0]["message"]["content"] == '{"ok": true}'


def test_anthropic_payload_preserves_multimodal_image() -> None:
    payload = OpenAICompatibleLLMProvider._anthropic_payload(
        [
            {"role": "system", "content": "Return JSON."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Identify this image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,aGVyYg=="},
                    },
                ],
            },
        ]
    )

    blocks = payload["messages"][0]["content"]
    assert blocks[0] == {"type": "text", "text": "Identify this image."}
    assert blocks[1]["source"] == {
        "type": "base64",
        "media_type": "image/png",
        "data": "aGVyYg==",
    }


@pytest.mark.asyncio
async def test_runtime_model_config_drives_cloud_vision(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    image = tmp_path / "herb.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    runtime_model_registry.set(
        user_id=9,
        learner_id="stu_009",
        protocol="openai",
        base_url="https://vision.example.test/v1",
        model_name="vision-test-model",
        api_key="vision-test-key",
    )
    captured: dict[str, object] = {}

    async def fake_complete_text(provider, messages, *, temperature, max_tokens):
        captured["provider"] = provider
        captured["messages"] = messages
        captured["temperature"] = temperature
        captured["max_tokens"] = max_tokens
        return "无法识别"

    monkeypatch.setattr(
        OpenAICompatibleLLMProvider,
        "complete_text",
        fake_complete_text,
    )
    try:
        result = await QwenVisionProvider().recognize(
            str(image),
            ModelCallContext(
                learner_id="stu_009",
                file_id="file_test",
                agent_code="vision_qwen",
            ),
        )
    finally:
        runtime_model_registry.clear(9)

    provider = captured["provider"]
    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.model_name == "vision-test-model"
    assert provider.settings.model_api_base_url == "https://vision.example.test/v1"
    assert result.provider == "qwen"
    assert result.model_name == "vision-test-model"
    assert result.candidate is not None
    assert result.candidate.herb_name == "无法识别"
    assert captured["temperature"] == 0
    assert captured["max_tokens"] == 16
    image_url = captured["messages"][1]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
