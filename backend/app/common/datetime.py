from datetime import UTC, datetime, timedelta, timezone

API_TIMEZONE = timezone(timedelta(hours=8))


def to_api_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(API_TIMEZONE).isoformat()


def now_api_datetime() -> str:
    return datetime.now(API_TIMEZONE).isoformat()
