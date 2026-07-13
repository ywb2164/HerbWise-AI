from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

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
        *,
        api_key: SecretStr | None = None,
        protocol: str = "openai",
    ) -> None:
        if protocol not in {"openai", "anthropic"}:
            raise ValueError("Unsupported model protocol")
        self.settings = settings or get_settings()
        self.model_name = model_name
        self.credential_reference = credential_reference
        self.api_key = api_key
        self.protocol = protocol

    def _credentials(self) -> tuple[str, str]:
        base_url = self.settings.model_api_base_url or self.settings.llm_base_url
        if not base_url:
            raise ProviderUnavailableError(
                "Model API base URL is not configured", error_code="configuration_error"
            )
        if self.api_key is not None and self.api_key.get_secret_value():
            return base_url.rstrip("/"), self.api_key.get_secret_value()
        reference = self.credential_reference or (
            "env:MODEL_API_KEY"
            if self.settings.model_api_key.get_secret_value()
            else "env:LLM_API_KEY"
        )
        return base_url.rstrip("/"), SecretResolver.resolve(reference)

    @staticmethod
    def _anthropic_content(content: object) -> object:
        if not isinstance(content, list):
            return str(content)
        blocks: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                blocks.append({"type": "text", "text": str(item.get("text", ""))})
                continue
            if item.get("type") != "image_url":
                continue
            image_url = item.get("image_url")
            url = image_url.get("url") if isinstance(image_url, dict) else None
            if not isinstance(url, str) or not url.startswith("data:"):
                continue
            header, separator, encoded = url.partition(",")
            if not separator or ";base64" not in header:
                continue
            media_type = header[5:].split(";", 1)[0]
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": encoded,
                    },
                }
            )
        return blocks or str(content)

    @staticmethod
    def _anthropic_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
        system = "\n\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        )
        conversation = [
            {
                "role": "assistant" if message.get("role") == "assistant" else "user",
                "content": OpenAICompatibleLLMProvider._anthropic_content(
                    message.get("content", "")
                ),
            }
            for message in messages
            if message.get("role") != "system"
        ]
        payload: dict[str, Any] = {
            "messages": conversation,
            "max_tokens": 4096,
        }
        if system:
            payload["system"] = system
        return payload

    @staticmethod
    def _normalize_anthropic_response(body: dict[str, Any]) -> dict[str, Any]:
        blocks = body.get("content")
        if not isinstance(blocks, list):
            raise ProviderUnavailableError(
                "Invalid model response", error_code="invalid_response"
            )
        content = "".join(
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not content:
            raise ProviderUnavailableError(
                "Model response did not contain text",
                error_code="invalid_response",
            )
        return {
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": body.get("usage", {}),
        }

    async def _chat(
        self,
        messages: list[dict[str, Any]],
        *,
        json_mode: bool,
        retries: int | None = None,
    ) -> dict[str, Any]:
        base_url, api_key = self._credentials()
        if self.protocol == "anthropic":
            payload = {
                "model": self.model_name,
                **self._anthropic_payload(messages),
            }
            url = f"{base_url}/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            payload = {"model": self.model_name, "messages": messages}
            url = f"{base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
        if json_mode and self.protocol == "openai":
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
                        url,
                        headers=headers,
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
                        return (
                            self._normalize_anthropic_response(body)
                            if self.protocol == "anthropic"
                            else body
                        )
                except httpx.TimeoutException:
                    last_error = ProviderUnavailableError(
                        "Model request timed out", error_code="timeout_error"
                    )
                except httpx.NetworkError:
                    last_error = ProviderUnavailableError(
                        "Model network request failed", error_code="network_error"
                    )
                except (httpx.HTTPStatusError, ValueError):
                    last_error = ProviderUnavailableError(
                        "Model returned an invalid response",
                        error_code="invalid_response",
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
