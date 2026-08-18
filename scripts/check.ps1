$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    throw "Falta .venv. Ejecutá .\scripts\setup.ps1 primero."
}
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw "Se necesita pnpm 11 para verificar el frontend."
}

& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m ruff check src\mailmap tests\test_hito0_api.py tests\test_hito0_domain.py
& .\.venv\Scripts\python.exe -m mypy
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build

Write-Host "Batería completa aprobada."
