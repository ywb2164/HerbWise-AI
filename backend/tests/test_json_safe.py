from datetime import UTC, datetime

from app.common.json import json_safe


def test_json_safe_recursively_serializes_timezone_datetime() -> None:
    value = {
        "created_at": datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        "nested": [datetime(2026, 7, 11, 4, 0)],
    }

    result = json_safe(value)

    assert result == {
        "created_at": "2026-07-11T20:00:00+08:00",
        "nested": ["2026-07-11T12:00:00+08:00"],
    }
