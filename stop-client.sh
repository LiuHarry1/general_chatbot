#!/bin/bash

echo "Stopping React Frontend..."

# Kill processes on port 3000 (React dev server)
echo "Stopping React development server on port 3000..."
pids=$(lsof -ti:3000 2>/dev/null)

if [ -n "$pids" ]; then
    echo "Found React processes: $pids"
    kill -TERM $pids 2>/dev/null
    sleep 2
    
    # Force kill if still running
    remaining_pids=$(lsof -ti:3000 2>/dev/null)
    if [ -n "$remaining_pids" ]; then
        echo "Force stopping remaining React processes: $remaining_pids"
        kill -KILL $remaining_pids 2>/dev/null
    fi
    
    echo "React Frontend stopped successfully"
else
    echo "No React Frontend processes found on port 3000"
fi

# Also kill any React-related Node.js processes
pkill -f "react-scripts start" 2>/dev/null && echo "Stopped React development server"
