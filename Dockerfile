# === Dockerfile for MedEdBot ===
# Optimized for minimal size - uses Alpine Linux

FROM python:3.11-alpine

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal system dependencies
RUN apk add --no-cache \
    # Build dependencies for Python packages (will be removed after pip install)
    gcc musl-dev libffi-dev postgresql-dev \
    # Runtime dependencies (permanent)
    ca-certificates \
    # Health check tool
    wget

# Create non-root user for security (Alpine syntax)
# Using UID/GID 1000 for Synology compatibility
RUN addgroup -g 1000 -S appuser && adduser -u 1000 -S appuser -G appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies and cleanup build deps
RUN pip install --no-cache-dir -r requirements.txt \
    && apk del gcc musl-dev libffi-dev postgresql-dev

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/tts_audio /app/voicemail /app/logs && \
    chown -R appuser:appuser /app && \
    chmod 775 /app/tts_audio /app/voicemail /app/logs

# Switch to non-root user
USER appuser

# Health check for container monitoring (using wget instead of curl)
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-8080}/ || exit 1

# Default environment variables (can be overridden)
ENV PORT=8080 \
    LOG_LEVEL=info

# Expose port (Synology typically uses this for port mapping)
EXPOSE 8080

# Use exec form for proper signal handling
# 0.0.0.0 allows external connections (required for Docker/Synology)
# Use Python to run uvicorn with custom logging config
CMD ["sh", "-c", "python -c \"import uvicorn; from utils.uvicorn_logging import get_uvicorn_log_config; uvicorn.run('main:app', host='0.0.0.0', port=int('${PORT:-8080}'), workers=1, log_config=get_uvicorn_log_config())\""]