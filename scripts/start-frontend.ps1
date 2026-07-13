[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$UserPort = 5173,

    [ValidateRange(1, 65535)]
    [int]$AdminPort = 9528,

    [ValidateRange(5, 300)]
    [int]$StartupTimeoutSeconds = 60,

    [switch]$SkipInstall,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$userDirectory = Join-Path $repoRoot "frontend"
$adminDirectory = Join-Path $repoRoot "admin-frontend"
$runtimeDirectory = Join-Path $repoRoot ".runtime\frontend"
$statePath = Join-Path $runtimeDirectory "processes.json"
$learnerPageMarker = -join @([char]0x672C, [char]0x8349, [char]0x667A, [char]0x7B56)
$adminPageMarker = $learnerPageMarker + (-join @([char]0x7BA1, [char]0x7406, [char]0x7AEF))

function Get-RequiredCommand {
    param([Parameter(Mandatory = $true)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Required command '$Name' was not found in PATH."
    }
    return $command
}

function Assert-NodeVersion {
    param([Parameter(Mandatory = $true)]$NodeCommand)

    $versionText = (& $NodeCommand.Source --version).Trim().TrimStart("v").Split("-")[0]
    $version = [version]$versionText
    $minimumVersion = [version]"20.19.0"
    if ($version -lt $minimumVersion) {
        throw "Node.js $minimumVersion or newer is required. Current version: $version."
    }

    Write-Host "Node.js: v$version"
}

function Ensure-FrontendDependencies {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$ProjectDirectory,
        [Parameter(Mandatory = $true)][string]$ViteEntry,
        [Parameter(Mandatory = $true)]$PackageManager,
        [Parameter(Mandatory = $true)][string[]]$InstallArguments
    )

    if (Test-Path -LiteralPath $ViteEntry) {
        return
    }

    if ($SkipInstall) {
        throw "$Name dependencies are missing. Run this script again without -SkipInstall."
    }

    Write-Host "Installing $Name dependencies..."
    Push-Location $ProjectDirectory
    try {
        & $PackageManager.Source @InstallArguments
        if ($LASTEXITCODE -ne 0) {
            throw "$Name dependency installation failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path -LiteralPath $ViteEntry)) {
        throw "$Name dependencies were installed, but the Vite entry was not found: $ViteEntry"
    }
}

function Test-HttpEndpoint {
    param([Parameter(Mandatory = $true)][string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
    }
    catch {
        return $false
    }
}

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

function Get-ProjectPortOwner {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$ProjectDirectory,
        [Parameter(Mandatory = $true)][string]$ExpectedMarker
    )

    $ownerIds = @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    if ($ownerIds.Count -eq 0) {
        return $null
    }

    foreach ($ownerId in $ownerIds) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerId" -ErrorAction SilentlyContinue
        if (-not $owner -or -not $owner.CommandLine) {
            continue
        }

        $isProjectProcess = $owner.CommandLine.IndexOf(
            $ProjectDirectory,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -ge 0
        $isViteProcess = $owner.CommandLine.IndexOf(
            "vite",
            [System.StringComparison]::OrdinalIgnoreCase
        ) -ge 0

        $url = "http://localhost:$Port"
        $hasExpectedPage = $isViteProcess -and (Test-PageMarker -Url $url -Marker $ExpectedMarker)
        if ($isViteProcess -and ($isProjectProcess -or $hasExpectedPage)) {
            return Get-Process -Id $ownerId -ErrorAction Stop
        }
    }

    throw "Port $Port is already occupied by a process outside this HerbWise-AI frontend."
}

function Wait-FrontendReady {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)]$Process,
        [Parameter(Mandatory = $true)][string]$ErrorLog
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpEndpoint -Url $Url) {
            Write-Host "$Name ready: $Url"
            return
        }

        $Process.Refresh()
        if ($Process.HasExited) {
            $details = ""
            if (Test-Path -LiteralPath $ErrorLog) {
                $details = (Get-Content -LiteralPath $ErrorLog -Tail 30) -join [Environment]::NewLine
            }
            throw "$Name exited before it became ready. Log: $ErrorLog`n$details"
        }

        Start-Sleep -Seconds 1
    }

    throw "$Name did not become ready within $StartupTimeoutSeconds seconds. Log: $ErrorLog"
}

function Start-ViteFrontend {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$ProjectDirectory,
        [Parameter(Mandatory = $true)][string]$ViteEntry,
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)]$NodeCommand,
        [Parameter(Mandatory = $true)][string]$ExpectedMarker,
        [string]$Mode
    )

    $url = "http://localhost:$Port"
    $existingProcess = Get-ProjectPortOwner `
        -Port $Port `
        -ProjectDirectory $ProjectDirectory `
        -ExpectedMarker $ExpectedMarker
    if ($existingProcess) {
        Write-Host "$Name is already running (PID $($existingProcess.Id))."
        Wait-FrontendReady -Name $Name -Url $url -Process $existingProcess -ErrorLog "not available"
        return [pscustomobject]@{
            Name = $Name
            Port = $Port
            Url = $url
            Process = $existingProcess
            StartedNow = $false
        }
    }

    $logPrefix = if ($Name -eq "Learner frontend") { "learner" } else { "admin" }
    $outputLog = Join-Path $runtimeDirectory "$logPrefix.stdout.log"
    $errorLog = Join-Path $runtimeDirectory "$logPrefix.stderr.log"
    Remove-Item -LiteralPath $outputLog, $errorLog -Force -ErrorAction SilentlyContinue

    $arguments = @(
        ('"{0}"' -f $ViteEntry)
    )
    if ($Mode) {
        $arguments += @("--mode", $Mode)
    }
    $arguments += @("--host", "0.0.0.0", "--port", $Port.ToString(), "--strictPort")

    $process = Start-Process `
        -FilePath $NodeCommand.Source `
        -ArgumentList $arguments `
        -WorkingDirectory $ProjectDirectory `
        -RedirectStandardOutput $outputLog `
        -RedirectStandardError $errorLog `
        -WindowStyle Hidden `
        -PassThru

    Write-Host "Starting $Name (PID $($process.Id))..."
    Wait-FrontendReady -Name $Name -Url $url -Process $process -ErrorLog $errorLog

    return [pscustomobject]@{
        Name = $Name
        Port = $Port
        Url = $url
        Process = $process
        StartedNow = $true
    }
}

if (-not (Test-Path -LiteralPath $userDirectory)) {
    throw "Learner frontend directory not found: $userDirectory"
}
if (-not (Test-Path -LiteralPath $adminDirectory)) {
    throw "Admin frontend directory not found: $adminDirectory"
}
if ($UserPort -eq $AdminPort) {
    throw "UserPort and AdminPort must be different."
}

New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null

$nodeCommand = Get-RequiredCommand -Name "node"
$npmCommand = Get-RequiredCommand -Name "npm.cmd"
$pnpmCommand = Get-RequiredCommand -Name "pnpm.cmd"
Assert-NodeVersion -NodeCommand $nodeCommand

$userViteEntry = Join-Path $userDirectory "node_modules\vite\bin\vite.js"
$adminViteEntry = Join-Path $adminDirectory "node_modules\vite\bin\vite.js"

Ensure-FrontendDependencies `
    -Name "learner frontend" `
    -ProjectDirectory $userDirectory `
    -ViteEntry $userViteEntry `
    -PackageManager $npmCommand `
    -InstallArguments @("ci")

Ensure-FrontendDependencies `
    -Name "admin frontend" `
    -ProjectDirectory $adminDirectory `
    -ViteEntry $adminViteEntry `
    -PackageManager $pnpmCommand `
    -InstallArguments @("install", "--frozen-lockfile")

$startedProcessIds = @()
try {
    $userService = Start-ViteFrontend `
        -Name "Learner frontend" `
        -ProjectDirectory $userDirectory `
        -ViteEntry $userViteEntry `
        -Port $UserPort `
        -NodeCommand $nodeCommand `
        -ExpectedMarker $learnerPageMarker
    if ($userService.StartedNow) {
        $startedProcessIds += $userService.Process.Id
    }

    $previousPortalUrl = $env:VITE_PORTAL_URL
    $env:VITE_PORTAL_URL = $userService.Url
    try {
        $adminService = Start-ViteFrontend `
            -Name "Admin frontend" `
            -ProjectDirectory $adminDirectory `
            -ViteEntry $adminViteEntry `
            -Port $AdminPort `
            -NodeCommand $nodeCommand `
            -ExpectedMarker $adminPageMarker `
            -Mode "test"
    }
    finally {
        $env:VITE_PORTAL_URL = $previousPortalUrl
    }
    if ($adminService.StartedNow) {
        $startedProcessIds += $adminService.Process.Id
    }

    $state = [ordered]@{
        startedAt = (Get-Date).ToString("o")
        repository = $repoRoot
        user = [ordered]@{
            pid = $userService.Process.Id
            port = $userService.Port
            url = $userService.Url
        }
        admin = [ordered]@{
            pid = $adminService.Process.Id
            port = $adminService.Port
            url = $adminService.Url
        }
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
}
catch {
    foreach ($processId in $startedProcessIds) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    throw
}

Write-Host ""
if (-not (Test-HttpEndpoint -Url "http://localhost:8000/health")) {
    Write-Warning "Backend is not reachable. Start it with .\scripts\start-dev.ps1"
}
else {
    Write-Host "Backend: http://localhost:8000/docs"
}
Write-Host "Learner: $($userService.Url)"
Write-Host "Admin:   $($adminService.Url)"
Write-Host "Logs:    $runtimeDirectory"
Write-Host "Stop:    .\scripts\stop-frontend.ps1"

if ($OpenBrowser) {
    Start-Process $userService.Url
}
