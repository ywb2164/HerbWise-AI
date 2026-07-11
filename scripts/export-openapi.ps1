[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..\backend")
try { uv run python scripts/export_openapi.py } finally { Pop-Location }
