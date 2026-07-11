[CmdletBinding()]
param([string]$InstallRoot = (Join-Path $PSScriptRoot "runtime"))
$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required." }
if (-not (Test-Path -LiteralPath $InstallRoot)) { throw "RAGFlow is not installed. Run install-ragflow.ps1 first." }
Push-Location $InstallRoot
try { docker compose up -d } finally { Pop-Location }
Write-Host "RAGFlow started. No volumes were removed."
