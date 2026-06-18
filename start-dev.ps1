# Start Manzil development environment (backend + frontend)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python3.12 -m venv (Join-Path $root ".venv")
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $root "backend\requirements.txt")
}

# Start backend
Write-Host "Starting FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .venv\Scripts\python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

# Wait for backend to be ready
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 1 -ErrorAction Stop
        $backendReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    Write-Host "Backend did not start in time. Check the backend window for errors." -ForegroundColor Red
    exit 1
}

Write-Host "Backend is ready." -ForegroundColor Green

# Start frontend
Write-Host "Starting Next.js frontend on http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

# Wait for frontend to be ready
$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $frontendReady) {
    Write-Host "Frontend did not start in time. Check the frontend window for errors." -ForegroundColor Red
    exit 1
}

Write-Host "Frontend is ready." -ForegroundColor Green
Write-Host ""
Write-Host "Open http://localhost:3000 in your browser." -ForegroundColor Magenta
