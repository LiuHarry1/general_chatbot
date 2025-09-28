@echo off

echo Starting Python Backend...

REM Check if .env exists in project root
if not exist ..\.env (
    echo Creating .env file from template...
    copy ..\env.example ..\.env
    echo.
    echo Please edit .env file and add your API keys before running again.
    echo.
    pause
    exit /b 1
)

REM Install Python dependencies if needed
if not exist requirements.txt (
    echo requirements.txt not found in server directory
    pause
    exit /b 1
)

echo Installing Python dependencies...
pip install -r requirements.txt
echo.

REM Create logs directory if it doesn't exist
if not exist logs (
    mkdir logs
)

REM Start Python backend server
echo Starting Python backend server on http://localhost:3001
python main.py
