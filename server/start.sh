#!/bin/bash

echo "Starting Python Backend..."

# Check if .env exists in project root
if [ ! -f ../.env ]; then
    echo "Creating .env file from template..."
    cp ../env.example ../.env
    echo
    echo "Please edit .env file and add your API keys before running again."
    echo
    exit 1
fi

# Install Python dependencies if needed
if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found in server directory"
    exit 1
fi

echo "Installing Python dependencies..."
pip install -r requirements.txt
echo

# Create logs directory if it doesn't exist
if [ ! -d logs ]; then
    mkdir -p logs
fi

# Start Python backend server
echo "Starting Python backend server on http://localhost:3001"
python main.py
