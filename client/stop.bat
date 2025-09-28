@echo off

echo Stopping React Frontend from client directory...

echo Stopping React development server on port 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo Killing React process %%a
    taskkill /PID %%a /F 2>nul
)

REM Kill any React-related Node.js processes
taskkill /F /IM node.exe /FI "WINDOWTITLE eq React Frontend*" 2>nul
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *react-scripts*" 2>nul

echo React Frontend stopped successfully!
pause
