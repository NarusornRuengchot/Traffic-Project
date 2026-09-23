#!/bin/bash
# ==============================================================================
# KU SRC Smart Traffic Analytics - Linux Server Startup Script
# Configured for University Cloud Container (Assigned Port: 3047)
# ==============================================================================

export PORT="${PORT:-3047}"
export HOST="${HOST:-0.0.0.0}"

echo "=========================================================="
echo "🚀 Starting KU SRC Smart Traffic Analytics on Linux Cloud"
echo "🌐 Public URL: http://119.59.102.161:${PORT}"
echo "📄 API Docs:   http://119.59.102.161:${PORT}/docs"
echo "=========================================================="

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    exit 1
fi

# Run the unified FastAPI + React SPA server
cd "$(dirname "$0")/../backend" || exit 1
python3 server.py
