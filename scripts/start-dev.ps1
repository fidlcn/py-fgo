# Start the FGO Bot dev stack on Windows: FastAPI backend + Vite frontend.
# Usage (PowerShell): ./scripts/start-dev.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Backend
$env:PYTHONUNBUFFERED = "1"
Start-Process -NoNewWindow python -ArgumentList "-m","uvicorn","backend.app:app","--reload","--host","127.0.0.1","--port","8765"

# Frontend (optional)
if (Test-Path "$root/frontend/package.json") {
    Push-Location "$root/frontend"
    if (-not (Test-Path "$root/frontend/node_modules")) { npm install }
    Start-Process -NoNewWindow npm -ArgumentList "run","dev"
    Pop-Location
}

Write-Host "Backend:  http://127.0.0.1:8765/docs"
Write-Host "Frontend: http://127.0.0.1:5173"
