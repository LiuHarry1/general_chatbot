#!/bin/bash

echo "Stopping Python Backend..."

# Kill processes on port 3001 (Python server)
echo "Stopping Python server on port 3001..."
pids=$(lsof -ti:3001 2>/dev/null)

if [ -n "$pids" ]; then
    echo "Found Python processes: $pids"
    kill -TERM $pids 2>/dev/null
    sleep 2
    
    # Force kill if still running
    remaining_pids=$(lsof -ti:3001 2>/dev/null)
    if [ -n "$remaining_pids" ]; then
        echo "Force stopping remaining Python processes: $remaining_pids"
        kill -KILL $remaining_pids 2>/dev/null
    fi
    
    echo "Python Backend stopped successfully"
else
    echo "No Python Backend processes found on port 3001"
fi

# Also kill any Python processes running our backend
pkill -f "main.py" 2>/dev/null && echo "Stopped Python backend server"
