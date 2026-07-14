[CmdletBinding()]
param(
    [switch]$NoBuild,
    [switch]$SkipSeed,
    [switch]$SkipModelCheck
)

$ErrorActionPreference = "Stop"

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ComposeFile = Join-Path $RepoRoot "compose.yaml"
$ComposeDevFile = Join-Path $RepoRoot "compose.dev.yaml"
$BackendEnvFile = Join-Path $RepoRoot "backend\.env"
$BackendEnvExampleFile = Join-Path $RepoRoot "backend\.env.example"
$MappingFile = Join-Path $RepoRoot "data\models\medicine-class-mapping.csv"
$ModelFile = Join-Path $RepoRoot "data\models\herbwise-yolo26s.pt"
$OriginalLocation = Get-Location
$script:ComposeArgs = @("compose", "-f", $ComposeFile, "-f", $ComposeDevFile)
$script:DockerEngineAvailable = $false
$script:DiagnosticsShown = $false

function Write-Step {
    param([string]$Message)

    Write-Host $Message -ForegroundColor Cyan
}

function Invoke-NativeCommand {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$NativeArguments
    )

    & $FilePath @NativeArguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Name failed (exit code $exitCode)."
    }
}

function Invoke-ComposeCommand {
    param(
        [string]$Name,
        [string[]]$ComposeArguments
    )

    Invoke-NativeCommand -Name $Name -FilePath "docker" -NativeArguments ($script:ComposeArgs + $ComposeArguments)
}

function Invoke-DiagnosticCommand {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$NativeArguments
    )

    try {
        & $FilePath @NativeArguments
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Warning "$Name failed while collecting diagnostics (exit code $exitCode)."
        }
    }
    catch {
        Write-Warning "$Name failed while collecting diagnostics: $($_.Exception.Message)"
    }
}

function Show-ComposeDiagnostics {
    param(
        [string[]]$Services = @("api", "db", "redis")
    )

    $script:DiagnosticsShown = $true
    Write-Host "Compose status:"
    Invoke-DiagnosticCommand -Name "docker compose ps" -FilePath "docker" -NativeArguments ($script:ComposeArgs + @("ps", "--all"))

    foreach ($service in $Services) {
        Write-Host "Recent $service logs:"
        Invoke-DiagnosticCommand -Name "docker compose logs $service" -FilePath "docker" -NativeArguments ($script:ComposeArgs + @("logs", "--tail", "100", $service))
    }
}

function Get-ComposeServices {
    # Compose JSON includes display-only fields (for example Command and Mounts) that
    # some Compose versions truncate into invalid JSON. Request only stable fields.
    $raw = Invoke-NativeCommand -Name "docker compose ps" -FilePath "docker" -NativeArguments ($script:ComposeArgs + @("ps", "--all", "--format", "{{.Service}}|{{.State}}|{{.Health}}"))
    $services = @()

    foreach ($item in $raw) {
        $line = ([string]$item).Trim()
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $parts = $line -split "\|", 3
        if ($parts.Count -lt 2 -or [string]::IsNullOrWhiteSpace($parts[0])) {
            throw "Unable to read docker compose service status: unexpected output '$line'."
        }

        $health = ""
        if ($parts.Count -eq 3) {
            $health = $parts[2]
        }
        $services += [PSCustomObject]@{
            Service = $parts[0]
            State = $parts[1]
            Health = $health
        }
    }

    return $services
}

function Get-ServiceValue {
    param(
        $Service,
        [string]$Name
    )

    if ($null -eq $Service) {
        return ""
    }

    $property = $Service.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) {
        return ""
    }
    return [string]$property.Value
}

function Get-ServiceInfo {
    param(
        [object[]]$Services,
        [string]$Name
    )

    foreach ($service in $Services) {
        if ((Get-ServiceValue $service "Service") -eq $Name) {
            return $service
        }
    }
    return $null
}

function Test-ApiHealthEndpoint {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/health" -TimeoutSec 5
        if ($response.StatusCode -ne 200) {
            return $false
        }

        $content = [string]$response.Content
        if ($content.TrimStart().StartsWith("{")) {
            $body = $content | ConvertFrom-Json
            $status = Get-ServiceValue $body "status"
            if ($status -match "^(unhealthy|failed|error)$") {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
}

function Wait-ForServices {
    $deadline = (Get-Date).AddSeconds(120)
    $attempt = 0

    while ($true) {
        $attempt++
        $services = Get-ComposeServices
        $db = Get-ServiceInfo $services "db"
        $redis = Get-ServiceInfo $services "redis"
        $api = Get-ServiceInfo $services "api"

        $dbHealth = Get-ServiceValue $db "Health"
        $redisHealth = Get-ServiceValue $redis "Health"
        $apiState = Get-ServiceValue $api "State"
        $apiHealth = Get-ServiceValue $api "Health"
        $apiReady = $apiState -eq "running"
        if ($apiReady -and -not [string]::IsNullOrWhiteSpace($apiHealth)) {
            $apiReady = $apiHealth -eq "healthy"
        }
        elseif ($apiReady) {
            $apiReady = Test-ApiHealthEndpoint
        }

        Write-Host ("  Waiting ({0}): db={1}; redis={2}; api={3}{4}" -f $attempt, $dbHealth, $redisHealth, $apiState, $(if ([string]::IsNullOrWhiteSpace($apiHealth)) { "" } else { "/$apiHealth" }))

        if ($dbHealth -eq "healthy" -and $redisHealth -eq "healthy" -and $apiReady) {
            return
        }

        if ((Get-Date) -ge $deadline) {
            Show-ComposeDiagnostics
            throw "Timed out after 120 seconds waiting for db and redis to become healthy and api to become ready."
        }
        Start-Sleep -Seconds 3
    }
}

try {
    Set-Location -LiteralPath $RepoRoot

    Write-Step "[1/6] Checking Docker"
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is required but the 'docker' command was not found on PATH."
    }
    try {
        Invoke-NativeCommand -Name "docker info" -FilePath "docker" -NativeArguments @("info")
        $script:DockerEngineAvailable = $true
    }
    catch {
        throw "Docker Engine is unavailable. Docker Desktop may still be starting; wait until it shows 'Engine running'. If it remains unavailable, run 'wsl --shutdown' and then restart Docker Desktop."
    }
    Invoke-NativeCommand -Name "docker compose version" -FilePath "docker" -NativeArguments @("compose", "version")

    foreach ($file in @($ComposeFile, $ComposeDevFile)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Required Compose file was not found: $file"
        }
    }
    if (-not (Test-Path -LiteralPath $BackendEnvFile -PathType Leaf)) {
        if (Test-Path -LiteralPath $BackendEnvExampleFile -PathType Leaf) {
            throw "Missing backend/.env. Create it with: Copy-Item backend\.env.example backend\.env"
        }
        throw "Missing required backend/.env."
    }

    Write-Step "[2/6] Validating Compose configuration"
    Invoke-ComposeCommand "docker compose config" @("config", "--quiet")

    Write-Step "[3/6] Building and starting containers"
    $upArguments = @("up", "-d")
    if (-not $NoBuild) {
        $upArguments += "--build"
    }
    Invoke-ComposeCommand "docker compose up" $upArguments

    Write-Step "[4/6] Waiting for MySQL, Redis, and API"
    Wait-ForServices

    Write-Step "[5/6] Running migrations and seed"
    try {
        Invoke-ComposeCommand "Alembic migration" @("exec", "-T", "api", "uv", "run", "alembic", "upgrade", "head")
    }
    catch {
        Show-ComposeDiagnostics @("api", "db")
        throw
    }

    if ($SkipSeed) {
        Write-Host "  Seed skipped (-SkipSeed)."
    }
    else {
        try {
            Invoke-ComposeCommand "seed_data.py" @("exec", "-T", "api", "uv", "run", "python", "scripts/seed_data.py")
        }
        catch {
            Show-ComposeDiagnostics @("api")
            throw
        }
    }

    if (Test-Path -LiteralPath $MappingFile -PathType Leaf) {
        try {
            Invoke-ComposeCommand "import_medicine_class_mapping.py" @("exec", "-T", "api", "uv", "run", "python", "scripts/import_medicine_class_mapping.py", "/data/models/medicine-class-mapping.csv")
        }
        catch {
            Show-ComposeDiagnostics @("api")
            throw
        }
    }
    else {
        Write-Warning "Medicine class mapping was not found; skipping import: $MappingFile"
    }

    if ($SkipModelCheck) {
        Write-Host "  Local model check skipped (-SkipModelCheck)."
    }
    elseif (Test-Path -LiteralPath $ModelFile -PathType Leaf) {
        try {
            Invoke-ComposeCommand "local_model_doctor.py" @("exec", "-T", "api", "uv", "run", "python", "scripts/local_model_doctor.py", "--info")
        }
        catch {
            Show-ComposeDiagnostics @("api")
            throw
        }
    }
    else {
        Write-Warning "Local model file was not found; local vision mode is unavailable. Mock and Qwen modes can still be used."
    }

    Write-Step "[6/6] Verifying API"
    if (-not (Test-ApiHealthEndpoint)) {
        Show-ComposeDiagnostics @("api")
        throw "API health check failed: http://localhost:8000/health"
    }

    Write-Host ""
    Write-Host "Backend started successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "Health:"
    Write-Host "http://localhost:8000/health"
    Write-Host ""
    Write-Host "Swagger:"
    Write-Host "http://localhost:8000/docs"
    Write-Host ""
    Write-Host "API:"
    Write-Host "http://localhost:8000/api"
    Invoke-ComposeCommand "docker compose ps" @("ps")
}
catch {
    Write-Error "Backend startup failed: $($_.Exception.Message)"
    if ($script:DockerEngineAvailable -and -not $script:DiagnosticsShown) {
        Show-ComposeDiagnostics
    }
    exit 1
}
finally {
    Set-Location -LiteralPath $OriginalLocation.Path
}
