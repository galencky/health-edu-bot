# Synology Container Manager Logs Fix

## The Issue
Synology Container Manager may not show logs when:
1. Custom log filtering is applied
2. Log format doesn't match expected JSON structure
3. Health check logs are filtered

## Solution Options

### Option 1: Keep All Logs (Recommended for Container Manager)
Remove custom logging to see all logs in Container Manager:

```bash
# No custom filtering - all logs visible
sudo docker-compose -f docker-compose.synology.yml up -d --build
```

### Option 2: Filter Logs Only in SSH
Keep full logs for Container Manager, but filter when viewing via SSH:

```bash
# View filtered logs in SSH
sudo docker logs -f mededbot-v4 2>&1 | grep -v "HEAD / HTTP"

# Or create an alias
alias mededlogs='sudo docker logs -f mededbot-v4 2>&1 | grep -v "HEAD / HTTP"'
```

### Option 3: Use Synology Log Center
1. Go to **Log Center** in DSM
2. Create a filter rule for Docker logs
3. Filter out health check patterns

## Current Configuration
The current setup uses standard logging without filtering to ensure compatibility with Container Manager. Health check logs will appear but can be ignored or filtered when viewing.

## Viewing Logs

### Container Manager (GUI)
1. Open Container Manager
2. Click on container → Details → Log tab
3. All logs including health checks will be visible

### SSH (Filtered)
```bash
# Basic filtered view
sudo docker logs -f mededbot-v4 | grep -Ev "(HEAD|GET) / HTTP"

# Show only important logs
sudo docker logs -f mededbot-v4 | grep -E "(User|Gemini|ERROR|WARNING|✅|📧|🎯)"

# Show last 50 non-health-check entries
sudo docker logs mededbot-v4 2>&1 | grep -v "HEAD / HTTP" | tail -50
```

## Log Patterns to Look For
- `User [user_id]:` - User messages
- `Gemini reply:` - AI responses  
- `✅ [DB]` - Database operations
- `📧 Email sent` - Email notifications
- `ERROR` - Error messages
- `WARNING` - Warning messages
- `🎯 STT result` - Speech recognition
- `🔊 TTS generated` - Text-to-speech