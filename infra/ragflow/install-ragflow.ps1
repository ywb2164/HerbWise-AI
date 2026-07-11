[CmdletBinding()]
param([string]$InstallRoot = (Join-Path $PSScriptRoot "runtime"))
$ErrorActionPreference = "Stop"
$version = "v0.20.5"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required. Install/start Docker, then run this command again." }
if (-not (Test-Path -LiteralPath $InstallRoot)) {
  git clone --branch $version --depth 1 https://github.com/infiniflow/ragflow.git $InstallRoot
}
Copy-Item (Join-Path $PSScriptRoot ".env.example") (Join-Path $InstallRoot ".env") -ErrorAction SilentlyContinue
Write-Host "RAGFlow $version prepared at $InstallRoot. Review its .env before starting."
