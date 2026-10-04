#!/usr/bin/env bash
# ==============================================================================
# BillTrack Launcher Script for Linux
# ==============================================================================

# Determine directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "=================================================="
echo " Starting BillTrack Server..."
echo "=================================================="

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found. Please install Python 3."
    exit 1
fi

# Start python server in background
python3 server.py 3000 &
SERVER_PID=$!

# Wait briefly for server to bind to port
sleep 1.5

URL="http://localhost:3000"
echo "✓ BillTrack Server is running on $URL (PID: $SERVER_PID)"
echo "Opening browser..."

# Open browser using xdg-open or fallback handlers
if command -v xdg-open > /dev/null; then
    xdg-open "$URL" > /dev/null 2>&1
elif command -v gnome-open > /dev/null; then
    gnome-open "$URL" > /dev/null 2>&1
elif command -v google-chrome > /dev/null; then
    google-chrome "$URL" > /dev/null 2>&1
elif command -v firefox > /dev/null; then
    firefox "$URL" > /dev/null 2>&1
else
    echo "Please open your browser and navigate to: $URL"
fi

echo ""
echo "Press Ctrl+C to stop the BillTrack Server."
echo "=================================================="

# Ensure server process is terminated on Ctrl+C or script exit
trap "echo -e '\nStopping BillTrack Server...'; kill $SERVER_PID 2>/dev/null; exit 0" SIGINT SIGTERM EXIT

wait $SERVER_PID
