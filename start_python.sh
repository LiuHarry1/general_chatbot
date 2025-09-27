#!/bin/bash

echo "Starting AI Assistant with Python Backend..."
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo
    echo "Please edit .env file and add your API keys before running again."
    echo
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d node_modules ]; then
    echo "Installing Node.js dependencies..."
    npm install
    echo
fi

if [ ! -d client/node_modules ]; then
    echo "Installing client dependencies..."
    cd client
    npm install
    cd ..
    echo
fi

# Install Python dependencies
echo "Installing Python dependencies..."
cd server
pip install -r requirements.txt
cd ..
echo

# Create logs directory
if [ ! -d logs ]; then
    mkdir logs
fi

# Start the application
echo "Starting AI Assistant..."
echo "Frontend will be available at: http://localhost:3000"
echo "Backend API will be available at: http://localhost:3001"
echo
npm run dev


