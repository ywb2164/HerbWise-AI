from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth.service import get_current_user
from app.modules.resources.models import UploadedFile
from app.modules.system import router as system_router
from app.modules.tasks.models import AgentLog, TaskEvent, TaskRecord


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    async def authenticated_user() -> object:
        return SimpleNamespace(
            roles=[SimpleNamespace(code="teacher")], is_superuser=False, learner_id=None
        )

    app.dependency_overrides[get_current_user] = authenticated_user
    with TestClient(app) as test_client:
        yield test_client


def test_business_endpoint_requires_authentication() -> None:
    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/agent/tasks/missing")

    assert response.status_code == 401
    assert response.json()["code"] == 1401


def test_ready_reports_dependencies(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def ok() -> None:
        return None

    monkeypatch.setattr(system_router, "check_database", ok)
    monkeypatch.setattr(system_router, "check_redis", ok)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
        "redis": "connected",
    }


def test_upload_and_get_file_contract(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    import app.modules.resources.router as resource_router

    now = datetime.now(UTC)
    record = UploadedFile(
        file_id="file_test",
        original_name="sample.png",
        relative_path="uploads/file_test.png",
        mime_type="image/png",
        size_bytes=7,
        sha256="0" * 64,
        created_at=now,
    )

    async def fake_save_upload(_upload):
        return record

    async def fake_get_uploaded_file(_file_id: str) -> UploadedFile:
        return record

    monkeypatch.setattr(resource_router, "save_upload", fake_save_upload)
    monkeypatch.setattr(resource_router, "get_uploaded_file", fake_get_uploaded_file)

    upload_response = client.post(
        "/api/files/upload",
        files={"file": ("sample.png", b"pngdata", "image/png")},
    )
    get_response = client.get("/api/files/file_test")

    assert upload_response.status_code == 201
    assert upload_response.json()["file_id"] == "file_test"
    assert get_response.status_code == 200
    assert get_response.json()["relative_path"] == "uploads/file_test.png"


def test_task_create_query_events_and_logs(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    import app.modules.tasks.router as task_router

    now = datetime.now(UTC)
    task = TaskRecord(
        task_id="task_test",
        learner_id="stu_001",
        task_type="full_loop",
        status="queued",
        current_node="load_profile",
        progress=10,
        result_json=None,
        error_message=None,
        created_at=now,
        started_at=None,
        finished_at=None,
        updated_at=now,
    )
    event = TaskEvent(
        task_id="task_test",
        event_type="node_completed",
        node_name="load_profile",
        status="success",
        progress=10,
        summary="load_profile completed",
        payload_json={"profile": {}},
        elapsed_ms=1.0,
        created_at=now,
    )
    log = AgentLog(
        task_id="task_test",
        node_name="load_profile",
        model_name="mock",
        provider="mock",
        prompt_version="v1",
        input_summary=None,
        output_summary="mock node completed",
        status="success",
        elapsed_ms=1.0,
        error_message=None,
        created_at=now,
    )

    async def fake_create_agent_task(_payload) -> TaskRecord:
        return task

    async def fake_require_task(_task_id: str) -> TaskRecord:
        return task

    async def fake_get_task_events(_task_id: str) -> list[TaskEvent]:
        return [event]

    async def fake_get_task_logs(_task_id: str) -> list[AgentLog]:
        return [log]

    monkeypatch.setattr(task_router, "create_agent_task", fake_create_agent_task)
    monkeypatch.setattr(task_router, "require_task", fake_require_task)
    monkeypatch.setattr(task_router, "get_task_events", fake_get_task_events)
    monkeypatch.setattr(task_router, "get_task_logs", fake_get_task_logs)

    create_response = client.post(
        "/api/agent/tasks",
        json={
            "learner_id": "stu_001",
            "task_type": "full_loop",
            "image_id": "img_mock_001",
        },
    )
    task_response = client.get("/api/agent/tasks/task_test")
    events_response = client.get("/api/agent/tasks/task_test/events")
    logs_response = client.get("/api/agent/tasks/task_test/logs")

    assert create_response.status_code == 202
    assert create_response.json() == {"task_id": "task_test", "status": "queued"}
    assert task_response.status_code == 200
    assert task_response.json()["current_node"] == "load_profile"
    assert events_response.status_code == 200
    assert events_response.json()[0]["event"] == "node_completed"
    assert logs_response.status_code == 200
    assert logs_response.json()[0]["provider"] == "mock"


def test_task_response_preserves_utf8_chinese_and_timezone(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    import app.modules.tasks.router as task_router

    now = datetime(2026, 7, 11, 8, 20, 43, tzinfo=UTC)
    task = TaskRecord(
        task_id="task_utf8",
        learner_id="stu_001",
        task_type="full_loop",
        status="success",
        current_node="save_trace",
        progress=100,
        result_json={
            "recognition_result": {
                "candidate": {"herb_name": "黄芪", "english_name": "Astragalus"}
            },
            "review_result": {"summary": "模拟审核通过"},
            "knowledge_evidence": [{"document_name": "中国药典（示例）"}],
        },
        error_message=None,
        created_at=now,
        started_at=now,
        finished_at=now,
        updated_at=now,
    )

    async def fake_require_task(_task_id: str) -> TaskRecord:
        return task

    monkeypatch.setattr(task_router, "require_task", fake_require_task)

    response = client.get("/api/agent/tasks/task_utf8")
    payload = response.json()

    assert response.status_code == 200
    assert "charset=utf-8" in response.headers["content-type"]
    assert payload["created_at"] == "2026-07-11T16:20:43+08:00"
    assert payload["result"]["recognition_result"]["candidate"]["herb_name"] == "黄芪"
    assert "模拟审核通过" in payload["result"]["review_result"]["summary"]
    assert (
        payload["result"]["knowledge_evidence"][0]["document_name"]
        == "中国药典（示例）"
    )
