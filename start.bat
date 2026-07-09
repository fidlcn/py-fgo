@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo py-fgo Windows Launcher
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Please install Python 3.9+ and make sure py.exe is available.
        pause
        exit /b 1
    )
)

echo [2/4] Installing backend dependencies if needed...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install Python dependencies.
    pause
    exit /b 1
)

if exist "frontend\package.json" (
    if not exist "frontend\node_modules" (
        echo [3/4] Installing frontend dependencies...
        pushd frontend
        call npm install
        if errorlevel 1 (
            popd
            echo Failed to install frontend dependencies. Please install Node.js 18+.
            pause
            exit /b 1
        )
        popd
    ) else (
        echo [3/4] Frontend dependencies already installed.
    )
) else (
    echo [3/4] frontend/package.json not found.
    pause
    exit /b 1
)

echo [4/4] Starting backend and frontend...
set "ROOT=%cd%"
start "py-fgo backend" /D "%ROOT%" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host localhost --port 8765"
start "py-fgo frontend" /D "%ROOT%\frontend" cmd /k "npm run dev"

echo Waiting for services to start...
timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo Dashboard: http://localhost:5173
echo API docs:  http://localhost:8765/docs
echo.
echo Two command windows were opened. Close them to stop the services.
pause
