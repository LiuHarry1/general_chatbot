@echo off

echo Stopping Python Backend...

echo Stopping Python server on port 3001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3001') do (
    echo Killing Python process %%a
    taskkill /PID %%a /F 2>nul
)

REM Kill any Python processes running our backend
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Python Backend*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main*" 2>nul

echo Python Backend stopped successfully!
pause
