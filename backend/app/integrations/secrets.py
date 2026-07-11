"""Secret resolution for database configuration references.

The database only stores an environment-variable reference.  Values are never
serialized into an API response, model-call record, or application log.
"""

import os

from app.core.exceptions import AppException


class SecretConfigurationError(AppException):
    status_code = 503
    code = 1501


class SecretResolver:
    @staticmethod
    def resolve(reference: str | None) -> str:
        if not reference or not reference.startswith("env:"):
            raise SecretConfigurationError(
                "A credential environment reference is required"
            )
        variable = reference.removeprefix("env:")
        if not variable or not variable.replace("_", "").isalnum():
            raise SecretConfigurationError("Invalid credential environment reference")
        value = os.getenv(variable, "")
        if not value:
            raise SecretConfigurationError(
                "Required model credential is not configured"
            )
        return value

    @staticmethod
    def is_configured(reference: str | None) -> bool:
        try:
            SecretResolver.resolve(reference)
        except SecretConfigurationError:
            return False
        return True
