@echo off

echo Starting React Frontend...

REM Check if node_modules exists
if not exist node_modules (
    echo Installing client dependencies...
    npm install
    echo.
)

REM Start React development server
echo Starting React development server on http://localhost:3000
npm start
