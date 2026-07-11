from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.integrations.contracts import (
    RAGEvidence,
    RAGProvider,
    RAGQuery,
    RAGRetrievalResult,
)
from app.integrations.openai_compatible import ProviderUnavailableError
from app.integrations.secrets import SecretResolver


class RAGFlowProvider(RAGProvider):
    """Compatibility adapter; all RAGFlow paths are intentionally centralized here."""

    provider_name = "ragflow"
    _DATASETS = "/api/v1/datasets"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _config(self) -> tuple[str, str, str]:
        if not self.settings.ragflow_base_url or not self.settings.ragflow_dataset_id:
            raise ProviderUnavailableError(
                "RAGFlow configuration is missing", error_code="configuration_error"
            )
        return (
            self.settings.ragflow_base_url.rstrip("/"),
            SecretResolver.resolve("env:RAGFLOW_API_KEY"),
            self.settings.ragflow_dataset_id,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        base, key, _ = self._config()
        timeout = httpx.Timeout(
            self.settings.ragflow_read_timeout_seconds,
            connect=self.settings.ragflow_connect_timeout_seconds,
        )
        attempts = self.settings.ragflow_max_retries + 1
        error: ProviderUnavailableError | None = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(attempts):
                try:
                    response = await client.request(
                        method,
                        f"{base}{path}",
                        headers={"Authorization": f"Bearer {key}"},
                        **kwargs,
                    )
                    if response.status_code in {401, 403}:
                        raise ProviderUnavailableError(
                            "RAGFlow authentication failed",
                            error_code="authentication_error",
                        )
                    if response.status_code == 404:
                        raise ProviderUnavailableError(
                            "RAGFlow dataset or document was not found",
                            error_code="dataset_not_found",
                        )
                    if response.status_code == 429:
                        error = ProviderUnavailableError(
                            "RAGFlow rate limit reached", error_code="rate_limit_error"
                        )
                    elif response.status_code >= 500:
                        error = ProviderUnavailableError(
                            "RAGFlow service unavailable",
                            error_code="provider_unavailable",
                        )
                    else:
                        response.raise_for_status()
                        body = response.json()
                        if not isinstance(body, dict):
                            raise ProviderUnavailableError(
                                "Invalid RAGFlow response",
                                error_code="invalid_response",
                            )
                        return body
                except httpx.TimeoutException:
                    error = ProviderUnavailableError(
                        "RAGFlow request timed out", error_code="timeout_error"
                    )
                except httpx.NetworkError:
                    error = ProviderUnavailableError(
                        "RAGFlow network request failed", error_code="network_error"
                    )
                if error is None or error.error_code == "authentication_error":
                    break
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.2)
        raise error or ProviderUnavailableError("RAGFlow request failed")

    @staticmethod
    def _chunks(body: dict[str, Any]) -> list[dict[str, Any]]:
        data = body.get("data", body)
        if isinstance(data, dict):
            for key in ("chunks", "results", "documents"):
                if isinstance(data.get(key), list):
                    return [item for item in data[key] if isinstance(item, dict)]
        return []

    async def retrieve_detailed(self, query: RAGQuery) -> RAGRetrievalResult:
        started = time.perf_counter()
        _, _, dataset_id = self._config()
        body = await self._request(
            "POST",
            f"{self._DATASETS}/{dataset_id}/retrieval",
            json={
                "question": query.query,
                "top_k": query.top_k,
                "similarity_threshold": query.score_threshold,
            },
        )
        evidences: list[RAGEvidence] = []
        for index, item in enumerate(self._chunks(body), start=1):
            content = str(item.get("content") or item.get("text") or "").strip()
            if not content:
                continue
            score = float(item.get("score") or item.get("similarity") or 0)
            if score < query.score_threshold:
                continue
            document_id = (
                str(item.get("document_id") or item.get("doc_id") or "") or None
            )
            chunk_id = str(item.get("chunk_id") or item.get("id") or "") or None
            document_name = str(
                item.get("document_name") or item.get("doc_name") or "Unknown document"
            )
            page = item.get("page_number") or item.get("page")
            page_number = (
                int(page)
                if isinstance(page, int | float | str) and str(page).isdigit()
                else None
            )
            citation = (
                f"{document_name}"
                + (f" p.{page_number}" if page_number is not None else "")
                + (f" [{chunk_id}]" if chunk_id else "")
            )
            evidences.append(
                RAGEvidence(
                    evidence_id=f"rag_{document_id or 'doc'}_{chunk_id or index}",
                    dataset_id=dataset_id,
                    document_id=document_id,
                    document_name=document_name,
                    chunk_id=chunk_id,
                    page_number=page_number,
                    section_title=item.get("section_title"),
                    content=content,
                    highlighted_content=item.get("highlight"),
                    score=min(1, max(0, score)),
                    vector_score=item.get("vector_score"),
                    keyword_score=item.get("keyword_score"),
                    rerank_score=item.get("rerank_score"),
                    source_type="ragflow",
                    citation=citation,
                    metadata={"external_id": item.get("id")},
                    data_source="ragflow",
                    rank=index,
                )
            )
        return RAGRetrievalResult(
            success=True,
            query=query.query,
            provider=self.provider_name,
            dataset_id=dataset_id,
            evidences=evidences[: query.top_k],
            total_candidates=len(self._chunks(body)),
            returned_count=min(len(evidences), query.top_k),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            data_source="ragflow",
        )

    async def retrieve(self, query: str):
        result = await self.retrieve_detailed(RAGQuery(query=query))
        from app.integrations.contracts import KnowledgeEvidence

        return [
            KnowledgeEvidence(
                chunk_id=item.chunk_id or item.evidence_id,
                content=item.content,
                document_name=item.document_name,
                page=item.page_number or 0,
                score=item.score,
                source_type=item.source_type,
            )
            for item in result.evidences
        ]

    async def health_check(self) -> dict[str, object]:
        _, _, dataset_id = self._config()
        await self._request("GET", f"{self._DATASETS}/{dataset_id}")
        return {"configured": True, "reachable": True, "dataset_id": dataset_id}

    async def list_documents(
        self, dataset_id: str | None = None
    ) -> list[dict[str, object]]:
        _, _, configured = self._config()
        body = await self._request(
            "GET", f"{self._DATASETS}/{dataset_id or configured}/documents"
        )
        return self._chunks(body)

    async def sync_document(self, document: dict[str, object]) -> dict[str, object]:
        _, _, dataset_id = self._config()
        return await self._request(
            "POST", f"{self._DATASETS}/{dataset_id}/documents", json=document
        )

    async def delete_document_mapping(self, external_document_id: str) -> None:
        _, _, dataset_id = self._config()
        await self._request(
            "DELETE", f"{self._DATASETS}/{dataset_id}/documents/{external_document_id}"
        )
