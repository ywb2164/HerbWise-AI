[CmdletBinding()]
param([switch]$Real)
$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required for the demo stack." }
if ($Real) { Write-Host "Real mode requested: only configured services will be checked; credentials are read from backend/.env." } else { Write-Host "Starting safe replay demo mode; no real model is invoked." }
docker compose -f compose.yaml -f compose.demo.yaml up -d --build
Push-Location (Join-Path $PSScriptRoot "..\backend")
try { uv run alembic upgrade head; uv run python scripts/seed_data.py; uv run python scripts/smoke_demo_replay.py } finally { Pop-Location }
Write-Host "Demo API: http://localhost:8000/docs"
