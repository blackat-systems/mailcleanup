$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Se necesita Python 3.11 o posterior disponible como 'python'."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Se necesita Node.js para preparar el frontend."
}
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw "Se necesita pnpm 11 para instalar el frontend."
}

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Falló la creación de .venv (código $LASTEXITCODE)." }
}
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación Python (código $LASTEXITCODE)." }
pnpm --dir frontend install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación frontend (código $LASTEXITCODE)." }
pnpm --dir frontend build
if ($LASTEXITCODE -ne 0) { throw "Falló el build frontend (código $LASTEXITCODE)." }

Write-Host "Entorno listo. Ejecutá .\scripts\run.ps1"
