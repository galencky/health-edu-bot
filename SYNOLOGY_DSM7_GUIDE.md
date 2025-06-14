# Synology DSM 7+ Deployment Guide for MedEdBot

This guide is specifically for Synology NAS running DSM 7.0 or later with Container Manager.

## 🔑 Key Changes for DSM 7+

- Uses **Container Manager** instead of Docker package
- Different permission model (more restrictive)
- Built-in container registry support
- Enhanced security features

## 📋 Prerequisites

1. **Synology NAS with DSM 7.0+**
2. **Container Manager** installed from Package Center
3. **SSH access** enabled (Control Panel → Terminal & SNMP)
4. **Shared folder** created (e.g., `docker` on volume1)

## 🚀 Quick Setup (Automated)

### Step 1: Enable SSH and Connect

```bash
# Enable SSH in DSM:
# Control Panel → Terminal & SNMP → Enable SSH service

# Connect from your computer:
ssh admin@your-nas-ip
```

### Step 2: Run Setup Script

```bash
# Download and run the setup script
sudo curl -L https://raw.githubusercontent.com/yourusername/mededbot/main/synology_setup.sh -o /tmp/setup.sh
sudo bash /tmp/setup.sh
```

## 🔧 Manual Setup (Step-by-Step)

### Step 1: Create Directory Structure

```bash
# SSH into your Synology NAS
ssh admin@your-nas-ip

# Create directories (as root)
sudo mkdir -p /volume1/docker/mededbot/{source,tts_audio,voicemail,logs,credentials}

# Set permissions (UID 1000 is Docker default)
sudo chown -R 1000:1000 /volume1/docker/mededbot
sudo chmod -R 755 /volume1/docker/mededbot
sudo chmod 775 /volume1/docker/mededbot/{tts_audio,voicemail,logs}
```

### Step 2: Upload Project Files

#### Option A: Using File Station
1. Open **File Station**
2. Navigate to `/docker/mededbot/source/`
3. Upload all project files (including Dockerfile, requirements.txt, etc.)

#### Option B: Using Git
```bash
cd /volume1/docker/mededbot/source
sudo git clone https://github.com/yourusername/mededbot.git .
sudo chown -R 1000:1000 .
```

### Step 3: Configure Environment

Create `/volume1/docker/mededbot/.env`:

```bash
sudo nano /volume1/docker/mededbot/.env
```

Add your configuration:

```env
# === REQUIRED Settings ===
DATABASE_URL=postgresql://user:pass@host/db?ssl=require
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret
GEMINI_API_KEY=your_gemini_key
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
BASE_URL=http://192.168.1.100:10001  # Your NAS IP

# === OPTIONAL Settings ===
PORT=10001
LOG_LEVEL=info

# === Google Drive (Optional) ===
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
# Option 1: Base64 encoded
GOOGLE_CREDS_B64=your_base64_creds
# Option 2: Use mounted file (see credentials setup)
```

### Step 4: Google Credentials Setup (Optional)

If using Google Drive with a service account file:

```bash
# Place your service account JSON in credentials folder
sudo cp /path/to/service-account.json /volume1/docker/mededbot/credentials/
sudo chown 1000:1000 /volume1/docker/mededbot/credentials/service-account.json
sudo chmod 600 /volume1/docker/mededbot/credentials/service-account.json
```

## 🐳 Container Deployment

### Option 1: Using Container Manager UI (Recommended)

1. **Open Container Manager**

2. **Create Project**:
   - Go to **Project** → **Create**
   - Name: `mededbot`
   - Path: `/docker/mededbot/source`
   - Source: **Upload** or **Git repository**

3. **Build Image**:
   - Container Manager will detect `Dockerfile`
   - Click **Build**
   - Wait for build to complete

4. **Create Container**:
   - Go to **Container** → **Create**
   - Select your built image
   - Container name: `mededbot`
   
5. **Configure Container**:

   **General Settings**:
   - Enable auto-restart: ✅
   - Resource limitation: 
     - CPU: Medium (or as needed)
     - Memory: 1GB (minimum)

   **Port Settings**:
   ```
   Local Port: 10001
   Container Port: 10001
   Protocol: TCP
   ```

   **Volume Settings**:
   ```
   Host Path                                    Container Path          Mode
   /docker/mededbot/tts_audio                 /app/tts_audio          Read/Write
   /docker/mededbot/voicemail                 /app/voicemail          Read/Write
   /docker/mededbot/logs                      /app/logs               Read/Write
   /docker/mededbot/.env                      /app/.env               Read Only
   /docker/mededbot/credentials/service-account.json  /app/credentials.json   Read Only
   ```

   **Environment Variables**:
   - Import from `.env` file
   - Or set manually in UI

### Option 2: Using Docker Compose (Advanced)

```bash
cd /volume1/docker/mededbot/source

# Build image
sudo docker-compose -f docker-compose.synology.yml build

# Start container
sudo docker-compose -f docker-compose.synology.yml up -d

# Check logs
sudo docker-compose -f docker-compose.synology.yml logs -f
```

## 🔒 Security Configuration

### Firewall Rules

1. **Container Manager** → **Network** → **Firewall**
2. Add rule:
   - Protocol: TCP
   - Port: 10001
   - Source: Your network (e.g., 192.168.1.0/24)
   - Action: Allow

### Reverse Proxy (Optional)

For HTTPS access, set up Synology's reverse proxy:

1. **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
2. Create rule:
   - Source: `https://bot.yourdomain.com:443`
   - Destination: `http://localhost:10001`

## 🧪 Testing

### Local Network Test

```bash
# Health check
curl http://your-nas-ip:10001/
# Should return: {"message": "✅ FastAPI LINE + Gemini bot is running.", ...}

# Test chat endpoint
curl -X POST http://your-nas-ip:10001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Storage Test

```bash
# Check if directories are writable
docker exec mededbot touch /app/tts_audio/test.txt
docker exec mededbot ls -la /app/tts_audio/
docker exec mededbot rm /app/tts_audio/test.txt
```

## 🔧 Troubleshooting

### Permission Issues

If you see permission denied errors:

```bash
# Fix ownership
sudo chown -R 1000:1000 /volume1/docker/mededbot
sudo chmod -R 755 /volume1/docker/mededbot
sudo chmod 775 /volume1/docker/mededbot/{tts_audio,voicemail,logs}

# Restart container
docker restart mededbot
```

### Container Won't Start

```bash
# Check logs
docker logs mededbot

# Common issues:
# 1. Port already in use
sudo netstat -tulpn | grep 10001

# 2. Environment variables missing
docker exec mededbot env | grep -E "(LINE|GEMINI|DATABASE)"

# 3. Volume mount issues
docker inspect mededbot | grep -A 10 Mounts
```

### Database Connection Issues

```bash
# Test from container
docker exec mededbot python -c "
import os
import asyncio
from utils.database import get_async_db_engine
print('Testing DB connection...')
engine = get_async_db_engine()
print('Success!')
"
```

## 📊 Monitoring

### Container Manager Dashboard

- View container status
- Monitor CPU/Memory usage
- Check logs in real-time
- Set up alerts

### Log Rotation

Add to **Task Scheduler**:

```bash
#!/bin/bash
# Rotate logs weekly
find /volume1/docker/mededbot/logs -name "*.log" -mtime +7 -delete
```

### Audio Cleanup

Schedule daily cleanup task:

```bash
#!/bin/bash
# Clean TTS files older than 24 hours
find /volume1/docker/mededbot/tts_audio -name "*.wav" -mtime +1 -delete
```

## 🚨 DSM 7+ Specific Notes

1. **User Permissions**: DSM 7+ is stricter about permissions. Always use UID/GID 1000 for Docker containers.

2. **Container Manager vs Docker**: Container Manager adds a UI layer but uses Docker underneath. CLI commands still work.

3. **Network Isolation**: Containers are more isolated by default. Ensure proper network configuration.

4. **Resource Limits**: DSM 7+ enforces resource limits more strictly. Monitor usage and adjust as needed.

## 🎉 Success Indicators

You know it's working when:

1. ✅ Container shows "Running" in Container Manager
2. ✅ Health check returns success at `http://your-nas-ip:10001/`
3. ✅ No permission errors in logs
4. ✅ TTS audio files appear in `/docker/mededbot/tts_audio/`
5. ✅ Database operations show "✅ [DB]" in logs

## 📱 LINE Webhook Configuration

Update your LINE Bot webhook to:
- **Local testing**: `http://your-nas-ip:10001/webhook`
- **Production**: `https://your-domain.com/webhook` (with reverse proxy)

## 🆘 Getting Help

If issues persist:
1. Check Container Manager logs
2. SSH and check Docker logs: `docker logs mededbot`
3. Verify all environment variables are set
4. Test each component individually
5. Check Synology system logs in Log Center

Remember: The key for Synology is getting the permissions right. When in doubt, check ownership and permissions!