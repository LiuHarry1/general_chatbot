#!/bin/bash

echo "Stopping AI Assistant services..."

# Function to kill processes by port
kill_by_port() {
    local port=$1
    local service_name=$2
    
    echo "Stopping $service_name on port $port..."
    
    # Find PIDs using the port
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "Found $service_name processes: $pids"
        # Kill processes gracefully first
        kill -TERM $pids 2>/dev/null
        
        # Wait a moment for graceful shutdown
        sleep 2
        
        # Force kill if still running
        local remaining_pids=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$remaining_pids" ]; then
            echo "Force stopping remaining $service_name processes: $remaining_pids"
            kill -KILL $remaining_pids 2>/dev/null
        fi
        
        echo "$service_name stopped successfully"
    else
        echo "No $service_name processes found on port $port"
    fi
}

# Stop frontend (React dev server on port 3000)
kill_by_port 3000 "React Frontend"

# Stop backend (Python server on port 3001)
kill_by_port 3001 "Python Backend"

# Also kill any Node.js processes that might be related to our project
echo "Checking for any remaining Node.js processes..."
pkill -f "react-scripts start" 2>/dev/null && echo "Stopped React development server"

# Also kill any Python processes running main.py
echo "Checking for any remaining Python processes..."
pkill -f "main.py" 2>/dev/null && echo "Stopped Python backend server"

echo
echo "All services stopped successfully!"
echo "If you still see running processes, you may need to stop them manually."
