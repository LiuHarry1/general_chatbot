@echo off

echo Stopping AI Assistant services...

REM Function to kill processes by port (using netstat and taskkill)
echo Stopping React Frontend on port 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo Killing process %%a
    taskkill /PID %%a /F 2>nul
)

echo Stopping Python Backend on port 3001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3001') do (
    echo Killing process %%a
    taskkill /PID %%a /F 2>nul
)

REM Kill any remaining Node.js processes related to React
echo Checking for any remaining Node.js processes...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq React Frontend*" 2>nul
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *react-scripts*" 2>nul

REM Kill any remaining Python processes
echo Checking for any remaining Python processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Python Backend*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main*" 2>nul

echo.
echo All services stopped successfully!
echo If you still see running processes, you may need to stop them manually.
pause
