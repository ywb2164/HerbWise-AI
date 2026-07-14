from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Literal, TypeAlias

from pydantic import SecretStr

ModelPurpose: TypeAlias = Literal["vision", "text"]
MODEL_PURPOSES: frozenset[str] = frozenset({"vision", "text"})


def mask_secret(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


@dataclass(frozen=True, slots=True)
class RuntimeModelConfig:
    user_id: int
    learner_id: str | None
    purpose: ModelPurpose
    protocol: str
    base_url: str
    model_name: str
    api_key: SecretStr
    configured_at: datetime

    def public_status(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "configured": True,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "model_id": self.model_name,
            "api_key_masked": mask_secret(self.api_key.get_secret_value()),
            "configured_at": self.configured_at,
            "storage": "server_memory",
        }


class RuntimeModelRegistry:
    """Keep user-provided credentials in process memory, isolated by purpose."""

    def __init__(self) -> None:
        self._by_user: dict[int, dict[ModelPurpose, RuntimeModelConfig]] = {}
        self._learner_owner: dict[str, int] = {}
        self._lock = RLock()

    @staticmethod
    def _purpose(purpose: str) -> ModelPurpose:
        if purpose not in MODEL_PURPOSES:
            raise ValueError("Model purpose must be vision or text")
        return purpose  # type: ignore[return-value]

    def set(
        self,
        *,
        user_id: int,
        learner_id: str | None,
        purpose: ModelPurpose,
        protocol: str,
        base_url: str,
        model_name: str,
        api_key: str | None,
    ) -> RuntimeModelConfig:
        purpose = self._purpose(purpose)
        with self._lock:
            previous = self._by_user.get(user_id, {}).get(purpose)
            resolved_key = api_key or (
                previous.api_key.get_secret_value() if previous is not None else ""
            )
            if not resolved_key:
                raise ValueError("API key is required")
            config = RuntimeModelConfig(
                user_id=user_id,
                learner_id=learner_id,
                purpose=purpose,
                protocol=protocol,
                base_url=base_url.rstrip("/"),
                model_name=model_name,
                api_key=SecretStr(resolved_key),
                configured_at=datetime.now(UTC),
            )
            self._by_user.setdefault(user_id, {})[purpose] = config
            if learner_id:
                self._learner_owner[learner_id] = user_id
            return config

    def get_for_user(
        self, user_id: int, purpose: ModelPurpose
    ) -> RuntimeModelConfig | None:
        purpose = self._purpose(purpose)
        with self._lock:
            return self._by_user.get(user_id, {}).get(purpose)

    def get_for_learner(
        self, learner_id: str | None, purpose: ModelPurpose
    ) -> RuntimeModelConfig | None:
        purpose = self._purpose(purpose)
        if not learner_id:
            return None
        with self._lock:
            owner = self._learner_owner.get(learner_id)
            return (
                self._by_user.get(owner, {}).get(purpose) if owner is not None else None
            )

    def clear(self, user_id: int, purpose: ModelPurpose) -> bool:
        purpose = self._purpose(purpose)
        with self._lock:
            configs = self._by_user.get(user_id)
            if configs is None:
                return False
            config = configs.pop(purpose, None)
            if configs:
                return config is not None
            self._by_user.pop(user_id, None)
            if config and config.learner_id:
                self._learner_owner.pop(config.learner_id, None)
            return config is not None

    def clear_all(self) -> None:
        with self._lock:
            self._by_user.clear()
            self._learner_owner.clear()


runtime_model_registry = RuntimeModelRegistry()
