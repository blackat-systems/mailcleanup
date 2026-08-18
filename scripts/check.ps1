$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    throw "Falta .venv. Ejecutá .\scripts\setup.ps1 primero."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Se necesita Node.js para verificar el frontend."
}
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw "Se necesita pnpm 11 para verificar el frontend."
}

& .\.venv\Scripts\python.exe -m pytest
if ($LASTEXITCODE -ne 0) { throw "Falló pytest (código $LASTEXITCODE)." }
& .\.venv\Scripts\python.exe -m ruff check src\mailmap tests
if ($LASTEXITCODE -ne 0) { throw "Falló Ruff (código $LASTEXITCODE)." }
& .\.venv\Scripts\python.exe -m mypy
if ($LASTEXITCODE -ne 0) { throw "Falló mypy (código $LASTEXITCODE)." }
pnpm --dir frontend lint
if ($LASTEXITCODE -ne 0) { throw "Falló ESLint (código $LASTEXITCODE)." }
pnpm --dir frontend test
if ($LASTEXITCODE -ne 0) { throw "Falló Vitest (código $LASTEXITCODE)." }
pnpm --dir frontend build
if ($LASTEXITCODE -ne 0) { throw "Falló el build frontend (código $LASTEXITCODE)." }

Write-Host "Batería completa aprobada."
