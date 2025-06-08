# === Dockerfile for MedEdBot ===
# Optimized for Docker and Synology NAS Container Manager

FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for audio processing
    ffmpeg \
    # Required for DNS resolution (MX record checks)
    dnsutils \
    # Useful for debugging
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/tts_audio /app/voicemail /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10001}/ping || exit 1

# Default environment variables (can be overridden)
ENV PORT=10001 \
    LOG_LEVEL=info

# Expose port (Synology typically uses this for port mapping)
EXPOSE 10001

# Use exec form for proper signal handling
# 0.0.0.0 allows external connections (required for Docker/Synology)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10001} --workers 1 --log-level ${LOG_LEVEL:-info}"]