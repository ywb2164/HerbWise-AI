import pytest

from app.integrations.vision import qwen
from app.integrations.vision.qwen import (
    QwenVisionProvider,
    clean_medicinal_name,
)
from app.modules.recognition.fusion import fuse_recognition
from app.integrations.contracts import RecognitionCandidate, VisionRecognitionResult


def test_single_name_cleanup_keeps_the_model_name_without_semantic_rewrite() -> None:
    assert clean_medicinal_name("蜂房") == "蜂房"
    assert clean_medicinal_name("蜂房。") == "蜂房"
    assert clean_medicinal_name("**蜂房**") == "蜂房"
    assert clean_medicinal_name("\n\n“蜂房。”\n说明") == "蜂房"


class _TextModel:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    async def complete_text(self, _messages, *, temperature, max_tokens) -> str:
        assert temperature == 0
        assert max_tokens == 16
        value = self.responses[self.calls]
        self.calls += 1
        return value


@pytest.mark.asyncio
async def test_long_response_retries_once_then_uses_single_name(
    monkeypatch, tmp_path
) -> None:
    image = tmp_path / "herb.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    model = _TextModel(["蜂房是一种常见中药材，具有很多用途", "蜂房"])
    monkeypatch.setattr(
        qwen, "_resolve_vision_llm", lambda _context: ("test", "qwen", model)
    )
    result = await QwenVisionProvider().recognize(str(image))
    assert model.calls == 2
    assert result.candidate is not None
    assert result.candidate.herb_name == "蜂房"


@pytest.mark.asyncio
async def test_second_noncompliant_response_returns_unrecognized(
    monkeypatch, tmp_path
) -> None:
    image = tmp_path / "herb.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    model = _TextModel(
        [
            "这是一段超过二十个中文字符的详细分析说明文字不应作为药材名",
            "仍然是一段超过二十个中文字符的详细分析说明文字不应展示",
        ]
    )
    monkeypatch.setattr(
        qwen, "_resolve_vision_llm", lambda _context: ("test", "qwen", model)
    )
    result = await QwenVisionProvider().recognize(str(image))
    assert model.calls == 2
    assert result.candidate is not None
    assert result.candidate.herb_name == "无法识别"


def test_yolo_and_catalog_cannot_replace_single_primary_name() -> None:
    qwen_result = VisionRecognitionResult(
        provider="qwen",
        candidate=RecognitionCandidate(herb_name="蜂房", confidence=0),
        recognized=True,
    )
    yolo_result = VisionRecognitionResult(
        provider="local",
        candidate=RecognitionCandidate(herb_name="瓦楞子", confidence=0.99),
    )
    fused = fuse_recognition(yolo_result, qwen_result)
    assert fused.final_candidate is not None
    assert fused.final_candidate.herb_name == "蜂房"
