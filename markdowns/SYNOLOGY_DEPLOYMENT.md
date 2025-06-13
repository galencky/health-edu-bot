# Synology NAS Docker Deployment Guide

This guide provides step-by-step instructions for deploying MedEdBot on your Synology NAS using Docker Container Manager.

## 📋 Prerequisites

- Synology NAS with DSM 7.0+ 
- Docker package installed from Package Center
- At least 1GB RAM available for the container
- Access to Synology File Station and Container Manager

## 🏗️ Directory Structure Setup

### 1. Create Directory Structure on Synology

Using File Station, create the following directory structure:

```
/volume1/docker/mededbot/
├── source/              # Your project files
├── tts_audio/          # TTS generated audio files
├── voicemail/          # Voice message files  
├── logs/               # Application logs
├── .env                # Environment variables
└── credentials.json    # Google service account (optional)
```

### 2. Create Required Directories

```bash
# SSH into your Synology NAS and run:
sudo mkdir -p /volume1/docker/mededbot/{source,tts_audio,voicemail,logs}
sudo chown -R 1000:1000 /volume1/docker/mededbot
```

## 📁 File Transfer

### Upload Project Files

1. **Using File Station:**
   - Upload all project files to `/volume1/docker/mededbot/source/`
   - Ensure all files including `Dockerfile`, `requirements.txt`, etc. are present

2. **Using SSH/SCP:**
   ```bash
   scp -r /path/to/Mededbot/* user@synology-ip:/volume1/docker/mededbot/source/
   ```

## ⚙️ Environment Configuration

### Create .env File

Create `/volume1/docker/mededbot/.env` with your configuration:

```env
# === Database Configuration ===
DATABASE_URL=postgresql://username:password@host/database?ssl=require

# === LINE Bot Configuration ===
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# === Google AI Configuration ===
GEMINI_API_KEY=your_gemini_api_key

# === Email Configuration ===
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# === Google Drive Configuration ===
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_CREDS_B64=your_base64_encoded_credentials

# === Server Configuration ===
BASE_URL=https://your-domain.com
# Or for local testing: BASE_URL=http://your-nas-ip:10001

# === Optional: Application Settings ===
PORT=10001
LOG_LEVEL=info
```

## 🐳 Docker Deployment

### Method 1: Using Container Manager (Recommended)

1. **Open Container Manager** in DSM
2. **Go to Image** → **Add** → **Add from URL**
3. **Build custom image:**
   - Click **Add** → **Create Docker image**
   - Select `/volume1/docker/mededbot/source` as source folder
   - Name: `mededbot`
   - Build the image

4. **Create Container:**
   - Go to **Container** → **Create**
   - Select `mededbot` image
   - Configure as follows:

#### Container Settings:
- **Container Name:** `mededbot`
- **Execution Command:** Keep default
- **Enable auto-restart:** ✅

#### Port Settings:
- **Local Port:** `10001` 
- **Container Port:** `10001`
- **Type:** `TCP`

#### Volume Settings:
```
Host Path                               Container Path      Type
/volume1/docker/mededbot/tts_audio     /app/tts_audio      rw
/volume1/docker/mededbot/voicemail     /app/voicemail      rw  
/volume1/docker/mededbot/logs          /app/logs           rw
/volume1/docker/mededbot/.env          /app/.env           ro
```

#### Environment Variables:
Import from `/volume1/docker/mededbot/.env` or set manually:
- `PORT=10001`
- `LOG_LEVEL=info`
- (Add all other variables from .env file)

#### Resource Limitations:
- **Memory Limit:** `1GB`
- **CPU Priority:** `Normal`

### Method 2: Using Docker Compose

1. **Upload docker-compose.synology.yml** to `/volume1/docker/mededbot/`

2. **SSH into Synology:**
   ```bash
   cd /volume1/docker/mededbot/source
   docker-compose -f docker-compose.synology.yml up -d
   ```

## 🔧 Network Configuration

### Port Forwarding (Optional)

If you want external access:

1. **Router Configuration:**
   - Forward external port (e.g., 8080) to Synology IP:10001

2. **Synology Firewall:**
   - Control Panel → Security → Firewall
   - Create rule to allow port 10001

3. **Update BASE_URL:**
   ```env
   BASE_URL=https://your-domain.com:8080
   ```

## 🏥 Health Monitoring

### Container Health Check

The container includes built-in health monitoring:
- **Endpoint:** `http://localhost:10001/`
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Retries:** 3

### Synology Monitoring

1. **Container Manager:**
   - Check container status in **Container** tab
   - View logs in **Log** tab

2. **Log Files:**
   - Application logs: `/volume1/docker/mededbot/logs/`
   - Container logs: Container Manager → Container → **Details** → **Log**

## 🔍 Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check container logs
docker logs mededbot

# Common causes:
# - Missing environment variables
# - Port conflicts
# - Permission issues
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
docker exec -it mededbot python -c "
import os
from utils.database import get_async_db_engine
print('DB URL:', os.getenv('DATABASE_URL')[:50] + '...')
"
```

#### 3. Google Drive Upload Issues
```bash
# Check Google credentials
docker exec -it mededbot python -c "
import os
print('Creds available:', bool(os.getenv('GOOGLE_CREDS_B64')))
print('Folder ID:', os.getenv('GOOGLE_DRIVE_FOLDER_ID'))
"
```

#### 4. Permission Issues
```bash
# Fix directory permissions
sudo chown -R 1000:1000 /volume1/docker/mededbot
sudo chmod -R 755 /volume1/docker/mededbot
```

### Log Analysis

#### View Container Logs:
```bash
# Follow logs in real-time
docker logs -f mededbot

# View recent logs
docker logs --tail 100 mededbot
```

#### Key Log Messages:
- `✅ [DB]` = Database operations successful
- `❌ [DB]` = Database operations failed
- `☁️ uploaded` = Google Drive upload successful
- `💾 local only` = File saved locally, Drive upload failed

## 🚀 Verification

### Test Deployment

1. **Health Check:**
   ```bash
   curl http://your-nas-ip:10001/
   # Should return: {"message": "✅ FastAPI LINE + Gemini bot is running.", ...}
   ```

2. **Test Chat Endpoint:**
   ```bash
   curl -X POST http://your-nas-ip:10001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello"}'
   ```

3. **Check Database:**
   - Use the provided `view_logs.py` script
   - Or query your Neon database directly

### LINE Webhook Setup

Update your LINE Bot webhook URL to:
```
https://your-domain.com/webhook
```

Or for testing:
```
http://your-nas-ip:10001/webhook
```

## 📊 Performance Tuning

### Resource Optimization

#### For Low-End NAS (2-4GB RAM):
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.3'
```

#### For High-End NAS (8GB+ RAM):
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
```

### Storage Considerations

- **TTS Audio:** ~50KB per file, auto-cleanup recommended
- **Voicemail:** ~100KB per file, persistent storage
- **Logs:** ~1MB per day, rotation configured (10MB max)

## 🔐 Security Best Practices

1. **Use non-root user** (already configured in Dockerfile)
2. **Restrict container permissions** (no-new-privileges)
3. **Firewall configuration** (limit access to necessary ports)
4. **Regular updates** (rebuild container with latest dependencies)
5. **Environment variable security** (use .env file, not environment variables in compose)

## 📱 Mobile Access

Configure Synology QuickConnect or VPN for secure mobile access to your bot logs and monitoring.

---

## 🆘 Support

If you encounter issues:

1. Check container logs first
2. Verify environment variables
3. Test database connectivity
4. Review Synology system logs
5. Create an issue with detailed error messages

The deployment is optimized for Synology NAS with automatic restarts, health monitoring, and efficient resource usage.