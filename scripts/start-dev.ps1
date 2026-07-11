[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required for the development stack." }
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
Push-Location (Join-Path $PSScriptRoot "..\backend")
try { uv run alembic upgrade head; uv run python scripts/seed_data.py } finally { Pop-Location }
Write-Host "Swagger: http://localhost:8000/docs"
