from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": subject,
            "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
