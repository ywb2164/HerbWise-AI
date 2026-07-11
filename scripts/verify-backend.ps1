[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
docker compose ps
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
  uv run alembic current; uv run python scripts/seed_data.py; uv run python scripts/seed_data.py
  uv run pytest -q; uv run ruff format --check .; uv run ruff check .; uv run mypy app
  uv run python scripts/smoke_v03b_fake.py; uv run python scripts/evaluate_rag_retrieval.py --mode fake
  uv run python scripts/smoke_demo_replay.py; uv run python scripts/smoke_degradation.py
} finally { Pop-Location }
