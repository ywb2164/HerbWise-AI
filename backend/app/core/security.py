"""Compatibility exports for authentication helpers.

New code should import from :mod:`app.modules.auth.service`.
"""

from datetime import timedelta

from app.modules.auth.service import _token


def create_access_token(subject: str) -> str:
    return _token(subject, "access", timedelta(minutes=60))[0]
