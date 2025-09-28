#!/bin/bash

echo "Starting AI Assistant..."
echo "This script will start both frontend and backend services."
echo

# Function to cleanup background processes
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting Python backend..."
cd server
./start.sh &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "Starting React frontend..."
cd client
./start.sh &
FRONTEND_PID=$!
cd ..

echo
echo "Both services are starting..."
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:3001"
echo "Press Ctrl+C to stop all services"
echo

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID