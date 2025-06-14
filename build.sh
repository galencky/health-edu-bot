#!/usr/bin/env bash
# Build script for Render deployment

set -e  # Exit on error

echo "Starting build process..."

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p tts_audio voicemail logs

# Set permissions
chmod 755 tts_audio voicemail logs

echo "Build completed successfully!"