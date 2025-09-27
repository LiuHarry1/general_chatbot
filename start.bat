@echo off
echo Starting AI Assistant...
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file from template...
    copy env.example .env
    echo.
    echo Please edit .env file and add your API keys before running again.
    echo.
    pause
    exit /b 1
)

REM Install dependencies if node_modules doesn't exist
if not exist node_modules (
    echo Installing dependencies...
    npm install
    echo.
)

if not exist client\node_modules (
    echo Installing client dependencies...
    cd client
    npm install
    cd ..
    echo.
)

REM Create logs directory
if not exist logs (
    mkdir logs
)

REM Start the application
echo Starting AI Assistant...
echo Frontend will be available at: http://localhost:3000
echo Backend API will be available at: http://localhost:3001
echo.
npm run dev


