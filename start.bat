@echo off

echo Starting AI Assistant...
echo This script will start both frontend and backend services.
echo.

REM Start backend in a new window
echo Starting Python backend...
start "Python Backend" cmd /c "cd server && start.bat"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo Starting React frontend...
start "React Frontend" cmd /c "cd client && start.bat"

echo.
echo Both services are starting...
echo Frontend: http://localhost:3000
echo Backend: http://localhost:3001
echo Check the opened windows for service status.
echo.
pause