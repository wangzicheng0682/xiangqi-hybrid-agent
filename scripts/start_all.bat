@echo off
echo ========================================
echo   Xiangqi AI System - Start All
echo ========================================
echo.

echo [1/3] Starting Neo4j...
start "Neo4j" cmd /k "cd /d D:\neo4j-community-2026.02.2\bin && neo4j console"
timeout /t 5 /nobreak > nul

echo [2/3] Starting Backend API...
start "Backend API" cmd /k "cd /d %~dp0.. && python -m uvicorn api.main:app --host 0.0.0.0 --port 8002"
timeout /t 3 /nobreak > nul

echo [3/3] Starting Frontend...
start "Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ========================================
echo   All services starting...
echo   - Neo4j: http://localhost:7474
echo   - Backend API: http://localhost:8002
echo   - Frontend: http://localhost:3000
echo ========================================
pause
