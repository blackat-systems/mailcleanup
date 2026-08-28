$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FrontendIndex = Join-Path $ProjectRoot "frontend\dist\index.html"
$HealthUrl = "http://127.0.0.1:8765/api/v1/health"
$ContextUrl = "http://127.0.0.1:8765/api/v2/context"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Falta .venv. Ejecutá .\scripts\setup.ps1 primero."
}

if (-not (Test-Path -LiteralPath $FrontendIndex)) {
    if (-not (Get-Command node -ErrorAction SilentlyContinue) -or
        -not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
        throw "Falta el frontend compilado y no están disponibles Node.js y pnpm. Ejecutá .\scripts\setup.ps1."
    }

    Write-Host "El frontend no estaba compilado. Lo preparo con las dependencias locales..."
    Push-Location $ProjectRoot
    try {
        pnpm --dir frontend build
        if ($LASTEXITCODE -ne 0) {
            throw "Falló el build frontend (código $LASTEXITCODE). Ejecutá .\scripts\setup.ps1."
        }
    }
    finally {
        Pop-Location
    }
}

$Health = $null
$Context = $null
try {
    $Health = Invoke-RestMethod -Method Get -Uri $HealthUrl -TimeoutSec 2
    $Context = Invoke-RestMethod -Method Get -Uri $ContextUrl -TimeoutSec 2
}
catch {
    $Health = $null
    $Context = $null
}

$IsMailCleanup = (
    $null -ne $Health -and
    $null -ne $Health.PSObject.Properties["status"] -and
    $null -ne $Health.PSObject.Properties["mode"] -and
    $null -ne $Health.PSObject.Properties["gmailConnected"] -and
    [string]$Health.status -eq "ok" -and
    [string]$Health.mode -eq "synthetic" -and
    $Health.gmailConnected -eq $false -and
    $null -ne $Context -and
    $null -ne $Context.PSObject.Properties["contractVersion"] -and
    $null -ne $Context.PSObject.Properties["dataMode"] -and
    [int]$Context.contractVersion -eq 1 -and
    [string]$Context.dataMode -eq "synthetic"
)

if ($IsMailCleanup) {
    Write-Host "MailCleanup ya está disponible en http://127.0.0.1:8765"
    return
}

$ExistingListener = Get-NetTCPConnection `
    -LocalAddress "127.0.0.1" `
    -LocalPort 8765 `
    -State Listen `
    -ErrorAction SilentlyContinue
if ($ExistingListener) {
    throw "El puerto 127.0.0.1:8765 está ocupado por otro proceso. Cerralo o liberá el puerto antes de iniciar MailCleanup."
}

Write-Host "Mapa de correo disponible en http://127.0.0.1:8765"
Write-Host "Presioná Ctrl+C para detenerlo."
Push-Location $ProjectRoot
try {
    & $PythonPath -m mailmap.main
    if ($LASTEXITCODE -ne 0) {
        throw "MailCleanup se detuvo con código $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
