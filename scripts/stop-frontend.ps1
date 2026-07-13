[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$statePath = Join-Path $repoRoot ".runtime\frontend\processes.json"
$learnerPageMarker = -join @([char]0x672C, [char]0x8349, [char]0x667A, [char]0x7B56)
$adminPageMarker = $learnerPageMarker + (-join @([char]0x7BA1, [char]0x7406, [char]0x7AEF))

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host "No frontend process state was found. Nothing to stop."
    exit 0
}

$state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
$stopped = 0

function Test-PageMarker {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Marker
    )

    $client = New-Object System.Net.WebClient
    $client.Encoding = [System.Text.Encoding]::UTF8
    try {
        $content = $client.DownloadString($Url)
        return $content.IndexOf($Marker, [System.StringComparison]::Ordinal) -ge 0
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

$services = @(
    [pscustomobject]@{ State = $state.user; Marker = $learnerPageMarker },
    [pscustomobject]@{ State = $state.admin; Marker = $adminPageMarker }
)

foreach ($entry in $services) {
    $service = $entry.State
    $processId = [int]$service.pid
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if (-not $owner) {
        continue
    }

    $isProjectProcess = $owner.CommandLine -and $owner.CommandLine.IndexOf(
        $repoRoot,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -ge 0
    $isViteProcess = $owner.CommandLine -and $owner.CommandLine.IndexOf(
        "vite",
        [System.StringComparison]::OrdinalIgnoreCase
    ) -ge 0
    $hasExpectedPage = $isViteProcess -and (Test-PageMarker -Url $service.url -Marker $entry.Marker)

    if (-not ($isViteProcess -and ($isProjectProcess -or $hasExpectedPage))) {
        Write-Warning "Skipped PID $processId because it is no longer a HerbWise-AI Vite process."
        continue
    }

    Stop-Process -Id $processId -Force
    Write-Host "Stopped $($service.url) (PID $processId)."
    $stopped++
}

Remove-Item -LiteralPath $statePath -Force
Write-Host "Frontend services stopped: $stopped"
