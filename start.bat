@echo off
echo ========================================
echo Starting Fintech Risk Agent Platform
echo ========================================
echo.

echo [1/2] Starting Backend Server (Port 8000)...
start "Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Waiting for backend to start...
timeout /t 3 /nobreak > nul

echo.
echo [2/2] Starting Frontend Dev Server (Port 3000)...
start "Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ========================================
echo Application Started Successfully!
echo ========================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/api-docs
echo ========================================
echo.
echo Press any key to close this window...
pause > nul
