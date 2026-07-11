from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel

from app.common.datetime import to_api_datetime


def json_safe(value: object) -> object:
    """Recursively convert application values into MySQL JSON-safe values."""
    if isinstance(value, datetime):
        return to_api_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return json_safe(value.value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value
