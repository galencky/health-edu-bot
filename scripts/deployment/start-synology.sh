#!/bin/sh
# Simple startup script for Synology compatibility

# Print environment for debugging
echo "Starting MededBot..."
echo "PORT: ${PORT:-8080}"
echo "Python version:"
python --version

# Start the application directly
exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1