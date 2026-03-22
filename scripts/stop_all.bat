@echo off
echo Stopping all services...

echo Stopping Backend API...
taskkill /f /im python.exe 2>nul

echo Stopping Node.js (Frontend)...
taskkill /f /im node.exe 2>nul

echo Stopping Neo4j...
cd /d D:\neo4j-community-2026.02.2\bin
neo4j stop 2>nul

echo.
echo All services stopped.
pause
