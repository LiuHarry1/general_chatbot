#!/bin/bash

echo "Starting React Frontend..."

# Check if node_modules exists
if [ ! -d node_modules ]; then
    echo "Installing client dependencies..."
    npm install
    echo
fi

# Start React development server
echo "Starting React development server on http://localhost:3000"
npm start
