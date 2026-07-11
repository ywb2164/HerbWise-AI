[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..\backend")
try {
  uv run python scripts/config_doctor.py --check all; uv run python scripts/ragflow_doctor.py --all
  uv run python scripts/ai_provider_doctor.py --all; uv run python scripts/local_model_doctor.py --info
  uv run python scripts/smoke_v03c_real.py
} finally { Pop-Location }
