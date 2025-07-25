# === Dockerfile for MedEdBot ===
# Optimized for production deployment (Render, Heroku, etc.)

FROM python:3.11-alpine

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal system dependencies
RUN apk add --no-cache \
    # Build dependencies for Python packages
    gcc musl-dev libffi-dev postgresql-dev \
    # Runtime dependencies
    ca-certificates \
    # Health check tool
    wget \
    # Ensure unbuffered output
    coreutils

# Create non-root user for security
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

# Health check for container monitoring
HEALTHCHECK --interval=45s --timeout=15s --start-period=90s --retries=3 \
    CMD wget --no-verbose --tries=2 --timeout=10 -O - http://localhost:${PORT:-8080}/health > /dev/null || exit 1

# Default environment variables
ENV PORT=8080 \
    LOG_LEVEL=info

# Expose port
EXPOSE 8080

# Use exec form for proper signal handling
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level ${LOG_LEVEL:-info}"]