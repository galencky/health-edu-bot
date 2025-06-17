#!/bin/bash
# Synology NAS deployment script for MededBot

echo "🚀 Deploying MededBot to Synology NAS..."

# Stop and remove existing container
echo "🛑 Stopping existing container..."
docker stop mededbot 2>/dev/null
docker rm mededbot 2>/dev/null

# Build the image
echo "🏗️ Building Docker image..."
docker build -f Dockerfile.synology-simple -t mededbot:latest .

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/tts_audio data/voicemail data/logs

# Run container with proper settings for Synology
echo "🚀 Starting container..."
docker run -d \
  --name mededbot \
  --restart unless-stopped \
  -p 10001:8080 \
  --env-file .env \
  -e PYTHONUNBUFFERED=1 \
  -e PORT=8080 \
  -v $(pwd)/data/tts_audio:/app/tts_audio \
  -v $(pwd)/data/voicemail:/app/voicemail \
  -v $(pwd)/data/logs:/app/logs \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  mededbot:latest

# Check if container started
sleep 3
if docker ps | grep -q mededbot; then
    echo "✅ Container started successfully!"
    echo ""
    echo "📋 Check status with:"
    echo "   docker ps"
    echo "   docker logs mededbot"
    echo ""
    echo "🌐 Access at: http://your-nas-ip:10001"
    echo ""
    echo "📊 Logs should be visible in Container Manager!"
else
    echo "❌ Container failed to start. Check logs:"
    echo "   docker logs mededbot"
    exit 1
fi