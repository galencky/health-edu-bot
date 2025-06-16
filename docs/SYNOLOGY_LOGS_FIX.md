# Synology Container Manager Logs Fix

## The Issue (RESOLVED)
Previously, Synology Container Manager didn't show logs due to:
1. Custom log filtering suppressing output
2. Log propagation disabled in uvicorn configuration
3. Health check logs being filtered by default

## Solution Implemented

### ✅ Container-Friendly Logging
The application now automatically detects container environments and uses appropriate logging:

- **Container Mode**: When `CONTAINER_LOGGING=true` (default in docker-compose files)
  - No log filtering applied
  - Log propagation enabled (`propagate: True`)
  - Container-friendly log format with process ID and timestamp
  - All logs visible in Container Manager

- **Local Development**: When `CONTAINER_LOGGING=false`
  - Health check filtering available via `FILTER_HEALTH_CHECKS=true`
  - Original logging behavior preserved

### 🔧 Environment Variables
The following environment variables control logging behavior:

```yaml
environment:
  - CONTAINER_LOGGING=true      # Enable container-friendly logging (default)
  - PYTHONUNBUFFERED=1         # Ensure real-time log output
  - LOG_LEVEL=info             # Control verbosity
  - FILTER_HEALTH_CHECKS=false # Disable health check filtering (default)
```

### 📋 Configuration Status
- ✅ **docker-compose.synology.yml**: Optimized for Container Manager
- ✅ **docker-compose.yml**: Updated with container logging
- ✅ **Dockerfile**: Already had `PYTHONUNBUFFERED=1`
- ✅ **uvicorn_logging.py**: Container-aware configuration

## Testing the Fix

### 🧪 Testing Logs
Check the container logs directly to verify logging is working properly.

### 📝 Deploy and Test Steps
1. **Rebuild the container**:
   ```bash
   sudo docker-compose -f docker-compose.synology.yml down
   sudo docker-compose -f docker-compose.synology.yml up -d --build
   ```

2. **Check Container Manager logs**:
   - Open Container Manager → Select mededbot-v4 → Details → Log tab
   - You should now see startup logs, health checks, and application logs

3. **Test logging**:
   ```bash
   # Check startup logs and application logs
   sudo docker logs mededbot-v4
   ```

## Viewing Logs

### Container Manager (GUI) ✅ 
1. Open Container Manager
2. Click on container → Details → Log tab  
3. **All logs now visible** including startup, health checks, and application events

### SSH (Optional Filtering)
```bash
# View all logs (recommended - same as Container Manager)
sudo docker logs -f mededbot-v4

# Optional: Filter out health checks if preferred
sudo docker logs -f mededbot-v4 | grep -Ev "(HEAD|GET) / HTTP"

# Show only application logs
sudo docker logs -f mededbot-v4 | grep -E "(User|Gemini|ERROR|WARNING|✅|📧|🎯|🧪)"
```

## Log Patterns to Look For
- `🧪 [TEST]` - Test logging entries  
- `✅ [DB]` - Database operations
- `🧠 Using in-memory storage` - Storage mode confirmation
- `User [user_id]:` - User messages
- `Gemini reply:` - AI responses  
- `📧 Email sent` - Email notifications
- `ERROR` / `WARNING` - Error/warning messages
- `🎯 STT result` - Speech recognition
- `🔊 TTS generated` - Text-to-speech
- HTTP access logs - Now visible in Container Manager

## Performance Notes
- **Logging Enabled**: Full visibility for debugging and monitoring
- **Performance Impact**: Minimal overhead from logging I/O
- **Disable Later**: Set `CONTAINER_LOGGING=false` and rebuild to reduce logging when stable