@echo off
echo ========================================
echo   Xiangqi AI System - Quick Start
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Kill existing processes on port 8003
echo [1/4] Stopping existing services...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Start Backend API
echo [2/4] Starting Backend API on port 8003...
start "Backend API" /min cmd /k "cd /d %~dp0 && python -m uvicorn api.main:app --host 0.0.0.0 --port 8003"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Check backend health
echo [3/4] Checking backend health...
curl -s http://localhost:8003/health >nul 2>&1
if errorlevel 0 (
    echo         Backend API: OK
) else (
    echo         Backend API: Starting...
)

REM Start Frontend
echo [4/4] Starting Frontend...
start "Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ========================================
echo   Services starting in new windows...
echo   - Backend API: http://localhost:8003
echo   - Frontend:    http://localhost:3000 (or next available port)
echo ========================================
echo.
echo Press any key to exit this window...
pause >nul
