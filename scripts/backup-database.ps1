[CmdletBinding()]
param([string]$OutputDirectory = (Join-Path $PSScriptRoot "..\data\backups"))
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$output = Join-Path $OutputDirectory "herbwise-$stamp.sql"
docker compose exec -T db sh -lc 'mysqldump -uherbwise -p"$MYSQL_PASSWORD" herbwise' | Out-File -LiteralPath $output -Encoding utf8
if (-not (Test-Path -LiteralPath $output) -or (Get-Item -LiteralPath $output).Length -eq 0) { throw "Database backup failed." }
Write-Host "Backup created: $output"
