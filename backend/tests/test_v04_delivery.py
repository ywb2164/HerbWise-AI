from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings
from app.integrations.contracts import RAGEvidence, RAGRetrievalResult
from app.modules.learning_paths.word_reports import (
    read_docx_text,
    safe_filename,
    write_docx,
)

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from scripts import (
    ai_provider_doctor,
    config_doctor,
    local_model_doctor,
    ragflow_doctor,
)
from scripts.doctor_common import Check, output


def test_config_doctor_does_not_render_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config_doctor,
        "get_settings",
        lambda: Settings(model_api_key="private-token-value"),
    )
    monkeypatch.setattr(config_doctor, "writable", lambda _path: (True, "writable"))
    result = config_doctor.checks("ai")
    rendered = " ".join(item.detail for item in result)
    assert "private-token-value" not in rendered
    assert any(item.name == "model_api_key" for item in result)


@pytest.mark.parametrize("scope", ["ai", "ragflow", "local-model", "all"])
def test_config_doctor_scopes(scope: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_doctor, "get_settings", lambda: Settings())
    monkeypatch.setattr(config_doctor, "writable", lambda _path: (True, "writable"))
    assert config_doctor.checks(scope)


@pytest.mark.asyncio
async def test_mock_ragflow_doctor_runs_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ragflow_doctor, "get_settings", lambda: Settings(rag_mode="mock")
    )
    result = await ragflow_doctor.run({"all"})
    assert {item.name for item in result} >= {"connection", "dataset", "retrieve"}
    assert all(item.status != "fail" for item in result)


@pytest.mark.asyncio
async def test_ai_doctor_mock_runs_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ai_provider_doctor, "get_settings", lambda: Settings(ai_mode="mock")
    )
    result = await ai_provider_doctor.run({"all"})
    assert [item.status for item in result] == ["pass", "pass", "pass"]


def test_local_model_disabled_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        local_model_doctor, "get_settings", lambda: Settings(local_vision_enabled=False)
    )
    assert local_model_doctor.model_checks()[0].status == "skipped"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a report.docx", "a_report.docx"),
        ("../../unsafe", "unsafe"),
        ("中文报告", "report"),
    ],
)
def test_safe_report_filename(raw: str, expected: str) -> None:
    assert safe_filename(raw) == expected


def test_word_writer_creates_readable_document(tmp_path: Path) -> None:
    target = tmp_path / "report.docx"
    write_docx(target, "学情报告", ["数据来源：mock", "不构成临床诊断或处方。"])
    assert target.is_file()
    text = read_docx_text(target)
    assert "学情报告" in text and "mock" in text


def test_replay_result_has_explicit_source_marker() -> None:
    response = RAGRetrievalResult(
        success=True,
        query="demo",
        provider="replay",
        replay_used=True,
        data_source="replay",
        evidences=[
            RAGEvidence(
                evidence_id="e",
                document_name="demo",
                chunk_id="chunk",
                content="content",
                score=1,
                source_type="replay",
                citation="demo [chunk]",
                data_source="replay",
            )
        ],
    )
    assert response.replay_used and response.evidences[0].citation


@pytest.mark.parametrize("status,code", [("pass", 0), ("skipped", 0), ("fail", 1)])
def test_doctor_exit_code(
    status: str, code: int, capsys: pytest.CaptureFixture[str]
) -> None:
    assert output([Check("sample", status, "safe")], False) == code
    assert "SECRET" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "script", ["smoke_demo_replay.py", "smoke_degradation.py", "smoke_v03c_real.py"]
)
def test_v04_smoke_scripts_are_safe(script: str) -> None:
    completed = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_repository_guard_passes_for_current_tree() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/repository_guard.py"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
