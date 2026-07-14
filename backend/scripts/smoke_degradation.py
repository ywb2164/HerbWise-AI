"""No-network degradation smoke for unavailable real providers and mock fallback."""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import Settings
from app.integrations.openai_compatible import (
    OpenAICompatibleLLMProvider,
    ProviderUnavailableError,
)
from app.integrations.rag.ragflow import RAGFlowProvider


async def main() -> int:
    settings = Settings(
        _env_file=None,
        model_api_base_url="",
        llm_base_url="",
        ragflow_base_url="",
        ragflow_dataset_id="",
    )
    try:
        await RAGFlowProvider(settings).health_check()
    except ProviderUnavailableError as exc:
        assert exc.error_code == "configuration_error"
    else:
        raise AssertionError("unconfigured RAGFlow must be unavailable")
    try:
        await OpenAICompatibleLLMProvider("demo", settings).generate_resource([])
    except ProviderUnavailableError as exc:
        assert exc.error_code == "configuration_error"
    else:
        raise AssertionError("unconfigured model must be unavailable")
    print(
        "Degradation smoke passed: missing real services fail safely without network calls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
