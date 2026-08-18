$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    throw "Falta .venv. Ejecutá .\scripts\setup.ps1 primero."
}
if (-not (Test-Path -LiteralPath ".\frontend\dist\index.html")) {
    throw "Falta el frontend compilado. Ejecutá .\scripts\setup.ps1 o pnpm --dir frontend build."
}

Write-Host "Mapa de correo disponible en http://127.0.0.1:8765"
Write-Host "Presioná Ctrl+C para detenerlo."
& .\.venv\Scripts\python.exe -m mailmap.main
