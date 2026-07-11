[CmdletBinding()]
param([string]$InstallRoot = (Join-Path $PSScriptRoot "runtime"))
$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required." }
if (-not (Test-Path -LiteralPath $InstallRoot)) { Write-Host "RAGFlow is not installed."; exit 0 }
Push-Location $InstallRoot
try { docker compose ps } finally { Pop-Location }
Write-Host "Default web/API port is configured by infra/ragflow/.env (9380 by default)."
