$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Se necesita Python 3.11 o posterior disponible como 'python'."
}
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw "Se necesita pnpm 11 para instalar el frontend."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build

Write-Host "Entorno listo. Ejecutá .\scripts\run.ps1"
