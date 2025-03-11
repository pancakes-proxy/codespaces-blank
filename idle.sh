#!/bin/bash

# Kill any currently running Node.js processes
echo "Stopping any running Node.js processes..."
pkill -f "node server.js"

# Wait for a moment to ensure the process is stopped
sleep 2

# Restart the Node.js server
echo "Restarting the server..."
node server.js &
