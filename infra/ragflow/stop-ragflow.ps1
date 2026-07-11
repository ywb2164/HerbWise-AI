[CmdletBinding()]
param([string]$InstallRoot = (Join-Path $PSScriptRoot "runtime"))
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $InstallRoot)) { throw "RAGFlow is not installed." }
Push-Location $InstallRoot
try { docker compose stop } finally { Pop-Location }
Write-Host "RAGFlow containers stopped; volumes were preserved."
