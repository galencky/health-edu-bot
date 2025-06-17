# MededBot Deployment Guide

## Quick Start

### Option 1: Standard Deployment (Render, Railway, VPS)
```bash
docker-compose up -d
```

### Option 2: Synology NAS Deployment
```bash
docker-compose -f docker-compose.synology.yml up -d
# Or use the deployment script:
./deploy-synology.sh
```

## Deployment Configurations

### 1. Standard Production (Dockerfile)
- **Base**: Alpine Linux (minimal size)
- **Security**: Non-root user
- **Health checks**: Built-in
- **Use for**: Render, Railway, Heroku, AWS, GCP, VPS

### 2. Synology NAS (Dockerfile.synology)
- **Base**: Python 3.11 (maximum compatibility)
- **Logging**: Unbuffered output for Container Manager
- **Simplified**: No health checks, minimal config
- **Use for**: Synology DSM 7+ Container Manager

## Environment Variables

Create a `.env` file with:

```env
# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret

# Gemini API
GEMINI_API_KEY=your_key

# Email (optional)
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Google Drive (optional)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_CREDS_B64=your_base64_encoded_credentials

# App Config
BASE_URL=https://your-domain.com
PORT=8080
DATABASE_URL=postgresql://user:pass@host/dbname
```

## Synology-Specific Notes

### Making Logs Visible
1. **Never use TTY mode** - `tty: false` in docker-compose
2. **Set PYTHONUNBUFFERED=1** - Already configured
3. **Use default log driver** - json-file

### If Container Manager logs are empty:
- Check Container > Details > Terminal (should show "unavailable")
- Recreate container without "Allocate pseudo-TTY" option
- Use SSH: `docker logs mededbot`

### OCI Runtime Errors
If you get "OCI runtime exec failed":
```bash
# Use the simplified Dockerfile
docker build -f Dockerfile.synology -t mededbot .
docker run -d --name mededbot -p 10001:8080 --env-file .env mededbot
```

## Architecture Improvements Applied

### Stability Enhancements
- ✅ Thread-safe session management with per-user locks
- ✅ Bounded thread pools (4 workers for Gemini, 5 for logging)
- ✅ Graceful task cancellation
- ✅ Memory cleanup for long-running deployments
- ✅ Enhanced error logging with stack traces

### Performance Optimizations
- Global connection pooling
- Reused thread executors
- Efficient session storage
- Automatic resource cleanup

## Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Logs
```bash
# Docker logs
docker logs -f mededbot

# Application logs (if volume mounted)
tail -f data/logs/*.log
```

### Session Info
```bash
curl http://localhost:8080/health | jq
```

## Troubleshooting

### High Memory Usage
- Check `docker stats mededbot`
- Memory cleanup runs hourly
- Restart if needed: `docker restart mededbot`

### Database Connection Issues
- Verify DATABASE_URL in .env
- Check network connectivity
- Look for connection pool exhaustion in logs

### LINE Webhook Failures
- Verify BASE_URL is publicly accessible
- Check LINE channel settings
- Monitor webhook endpoint: `/webhook`

## Migration Path

### From Old Version
1. Backup data directories
2. Update .env file
3. Pull latest code
4. Run: `docker-compose down && docker-compose up -d`

### Pydantic Session Migration (Future)
- Models ready in `models/session.py`
- Gradual migration path available
- See PYDANTIC_MIGRATION_PLAN.md for details