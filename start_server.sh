#!/bin/bash

# Kill any existing uvicorn processes
pkill -f uvicorn 2>/dev/null || echo "No uvicorn process to kill"

# Start the server with reload flag
echo "Starting Resume API server on port 8080..."
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload > api.log 2>&1 &

# Wait for server to start
sleep 5

# Check if server is running
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "Server started successfully! Available at http://localhost:8080"
    echo "Process ID: $(pgrep -f 'uvicorn main:app')"
    echo "Server logs are being written to api.log"
else
    echo "Server failed to start. Check api.log for details."
    tail -n 20 api.log
fi