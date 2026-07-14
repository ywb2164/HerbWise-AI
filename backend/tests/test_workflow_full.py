import pytest

from app.integrations.mock import MockLLMProvider, MockRAGProvider, MockVisionProvider
from app.modules.traces.models import TraceRecord
from app.workflows.graph import build_workflow


class FakeSession:
    def __init__(self, records: list[object]) -> None:
        self.records = records

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def add(self, record: object) -> None:
        self.records.append(record)

    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_mock_langgraph_full_flow_generates_events_logs_and_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.workflows.nodes.main as workflow_nodes

    events: list[tuple[str, str, int]] = []
    logs: list[tuple[str, str]] = []
    traces: list[object] = []

    async def fake_record_event(
        _task_id: str,
        node_name: str,
        status: str,
        progress: int,
        _summary: str,
        _elapsed_ms: float | None = None,
        _payload: dict | None = None,
    ) -> None:
        events.append((node_name, status, progress))

    async def fake_record_agent_log(
        _task_id: str,
        node_name: str,
        status: str,
        _elapsed_ms: float,
        _output_summary: str,
        _error_message: str | None = None,
    ) -> None:
        logs.append((node_name, status))

    monkeypatch.setattr(workflow_nodes, "record_event", fake_record_event)
    monkeypatch.setattr(workflow_nodes, "record_agent_log", fake_record_agent_log)
    monkeypatch.setattr(
        workflow_nodes, "get_vision_provider", lambda: MockVisionProvider()
    )
    monkeypatch.setattr(
        workflow_nodes, "get_llm_provider", lambda *args, **kwargs: MockLLMProvider()
    )
    monkeypatch.setattr(
        workflow_nodes, "get_rag_provider", lambda *args, **kwargs: MockRAGProvider()
    )
    monkeypatch.setattr(
        workflow_nodes, "async_session_factory", lambda: FakeSession(traces)
    )

    result = await build_workflow().ainvoke(
        {
            "task_id": "task_full",
            "learner_id": "stu_001",
            "image_id": "img_mock_001",
            "image_path": None,
            "retry_count": 0,
            "errors": [],
        }
    )

    assert result["current_node"] == "save_trace"
    assert result["progress"] == 100
    assert "trace_id" in result
    assert len(events) == 18
    assert len(logs) == 9
    assert isinstance(traces[0], TraceRecord)
    assert traces[0].task_id == "task_full"
