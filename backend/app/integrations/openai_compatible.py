from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.integrations.contracts import (
    GeneratedResource,
    KnowledgeEvidence,
    LLMProvider,
    ModelCallContext,
    PathUpdateResult,
    ReviewResult,
)
from app.integrations.secrets import SecretResolver


class ProviderUnavailableError(AppException):
    status_code = 503
    code = 1502

    def __init__(
        self, message: str, *, error_code: str = "provider_unavailable"
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


def extract_json(content: str) -> object:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    start = min(
        (index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0),
        default=-1,
    )
    if start < 0:
        raise ValueError("Response does not contain JSON")
    try:
        return json.loads(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("Response contains invalid JSON") from exc


class OpenAICompatibleLLMProvider(LLMProvider):
    """Small async OpenAI-compatible client without vendor fields in services."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        model_name: str,
        settings: Settings | None = None,
        credential_reference: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model_name = model_name
        self.credential_reference = credential_reference

    def _credentials(self) -> tuple[str, str]:
        base_url = self.settings.model_api_base_url or self.settings.llm_base_url
        if not base_url:
            raise ProviderUnavailableError(
                "Model API base URL is not configured", error_code="configuration_error"
            )
        reference = self.credential_reference or (
            "env:MODEL_API_KEY"
            if self.settings.model_api_key.get_secret_value()
            else "env:LLM_API_KEY"
        )
        return base_url.rstrip("/"), SecretResolver.resolve(reference)

    async def _chat(
        self,
        messages: list[dict[str, Any],],
        *,
        json_mode: bool,
        retries: int | None = None,
    ) -> dict[str, Any]:
        base_url, api_key = self._credentials()
        payload: dict[str, Any] = {"model": self.model_name, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        timeout = httpx.Timeout(
            self.settings.model_read_timeout_seconds,
            connect=self.settings.model_connect_timeout_seconds,
        )
        attempts = (
            retries if retries is not None else self.settings.model_max_retries
        ) + 1
        last_error: ProviderUnavailableError | None = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(attempts):
                try:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=payload,
                    )
                    if response.status_code in {401, 403}:
                        raise ProviderUnavailableError(
                            "Model authentication failed",
                            error_code="authentication_error",
                        )
                    if response.status_code == 429:
                        last_error = ProviderUnavailableError(
                            "Model rate limit reached", error_code="rate_limit_error"
                        )
                    elif response.status_code >= 500:
                        last_error = ProviderUnavailableError(
                            "Model service unavailable",
                            error_code="provider_unavailable",
                        )
                    else:
                        response.raise_for_status()
                        body = response.json()
                        if not isinstance(body, dict):
                            raise ProviderUnavailableError(
                                "Invalid model response", error_code="invalid_response"
                            )
                        return body
                except httpx.TimeoutException:
                    last_error = ProviderUnavailableError(
                        "Model request timed out", error_code="timeout_error"
                    )
                except httpx.NetworkError:
                    last_error = ProviderUnavailableError(
                        "Model network request failed", error_code="network_error"
                    )
                if last_error is None or last_error.error_code in {
                    "authentication_error",
                    "rate_limit_error",
                }:
                    break
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.2)
        raise last_error or ProviderUnavailableError("Model request failed")

    async def complete_structured(
        self,
        messages: list[dict[str, Any]],
        schema: type[BaseModel],
        context: ModelCallContext,
    ) -> BaseModel:
        del context
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        formatted = [
            *messages,
            {
                "role": "system",
                "content": f"Return only JSON matching this schema: {schema_hint}",
            },
        ]
        for correction in range(2):
            body = await self._chat(formatted, json_mode=True, retries=0)
            try:
                content = body["choices"][0]["message"]["content"]
                return schema.model_validate(extract_json(content))
            except (KeyError, TypeError, ValueError, ValidationError):
                if correction:
                    raise ProviderUnavailableError(
                        "Model JSON failed schema validation",
                        error_code="schema_validation_error",
                    )
                formatted.append(
                    {
                        "role": "user",
                        "content": "Correct the previous response. Return valid JSON only.",
                    }
                )
        raise ProviderUnavailableError(
            "Model JSON failed schema validation", error_code="schema_validation_error"
        )

    async def generate_resource(
        self, evidence: list[KnowledgeEvidence], context: ModelCallContext | None = None
    ) -> list[GeneratedResource]:
        context = context or ModelCallContext(agent_code="resource_generation")

        class ResourceList(BaseModel):
            resources: list[GeneratedResource]

        output = await self.complete_structured(
            [
                {
                    "role": "user",
                    "content": "Create factual learning resources using only this evidence: "
                    + json.dumps(
                        [item.model_dump() for item in evidence], ensure_ascii=False
                    ),
                }
            ],
            ResourceList,
            context,
        )
        return ResourceList.model_validate(output).resources

    async def review_resource(
        self,
        resources: list[GeneratedResource],
        context: ModelCallContext | None = None,
    ) -> ReviewResult:
        context = context or ModelCallContext(agent_code="resource_review")
        return await self.complete_structured(
            [
                {
                    "role": "user",
                    "content": "Review these learning resources and return the requested JSON: "
                    + json.dumps(
                        [item.model_dump() for item in resources], ensure_ascii=False
                    ),
                }
            ],
            ReviewResult,
            context,
        )  # type: ignore[return-value]

    async def diagnose_profile(self, learner_id: str) -> dict:
        return {"learner_id": learner_id, "level": "unknown"}

    async def update_learning_path(
        self, learner_id: str, review: ReviewResult
    ) -> PathUpdateResult:
        return PathUpdateResult(
            status=review.status, next_steps=[f"Review {learner_id} learning path"]
        )
