#!/usr/bin/env bash
# Start script for Render deployment

echo "Starting MedEdBot..."

# Export port if not set
export PORT=${PORT:-10001}

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port $PORT