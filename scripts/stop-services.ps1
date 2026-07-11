[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
docker compose stop
Write-Host "Services stopped. Containers and volumes were preserved."
