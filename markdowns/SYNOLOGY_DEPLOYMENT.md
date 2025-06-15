# 🚀 Synology NAS Deployment Guide for MedEdBot

This guide will help you deploy MedEdBot on your Synology NAS using Docker/Container Manager.

## 📋 Prerequisites

- Synology NAS with DSM 7.0 or later
- Container Manager installed from Package Center
- SSH access enabled
- At least 1GB free RAM
- Port 10001 available

## 🛠️ Step-by-Step Deployment

### Step 1: Enable SSH Access

1. Open **Control Panel** → **Terminal & SNMP**
2. Check **Enable SSH service**
3. Apply settings

### Step 2: Prepare the Environment

1. **SSH into your Synology NAS:**
   ```bash
   ssh admin@your-nas-ip
   ```

2. **Run the setup script:**
   ```bash
   sudo curl -L https://raw.githubusercontent.com/yourusername/mededbot/main/synology_setup.sh -o /tmp/setup.sh
   sudo bash /tmp/setup.sh
   ```

   This script will:
   - Create necessary directories
   - Set proper permissions (UID/GID 1000)
   - Create .env template
   - Set up maintenance scripts

### Step 3: Copy Project Files

1. **Using File Station (GUI):**
   - Open File Station
   - Navigate to `/docker/mededbot/`
   - Upload all project files (excluding .git, __pycache__, etc.)

2. **Using SCP (Command Line):**
   ```bash
   # From your local machine
   scp -r /path/to/mededbot/* admin@nas-ip:/volume1/docker/mededbot/
   ```

### Step 4: Configure Environment

1. **Edit the .env file:**
   ```bash
   sudo nano /volume1/docker/mededbot/.env
   ```

2. **Required configurations:**
   - `DATABASE_URL` - Your PostgreSQL connection string
   - `LINE_CHANNEL_ACCESS_TOKEN` - From LINE Developers Console
   - `LINE_CHANNEL_SECRET` - From LINE Developers Console
   - `GEMINI_API_KEY` - From Google AI Studio
   - `GMAIL_ADDRESS` - Your Gmail address
   - `GMAIL_APP_PASSWORD` - Gmail app-specific password
   - `BASE_URL` - Set to `http://your-nas-ip:10001`

3. **Optional Google Drive setup:**
   - `GOOGLE_DRIVE_FOLDER_ID` - Your Drive folder ID
   - Either:
     - `GOOGLE_CREDS_B64` - Base64 encoded service account JSON
     - Or place `service-account.json` in `/volume1/docker/mededbot/credentials/`

### Step 5: Build and Run

1. **Navigate to project directory:**
   ```bash
   cd /volume1/docker/mededbot
   ```

2. **Build and start the container:**
   ```bash
   sudo docker-compose -f docker-compose.synology.yml up -d --build
   ```

3. **Check logs:**
   ```bash
   sudo docker-compose -f docker-compose.synology.yml logs -f
   ```

### Step 6: Verify Deployment

1. **Test health endpoint:**
   ```bash
   curl http://localhost:10001/
   ```
   
   Should return:
   ```json
   {
     "message": "✅ FastAPI LINE + Gemini bot is running.",
     "timestamp": "2024-XX-XX XX:XX:XX"
   }
   ```

2. **Check container status in Container Manager:**
   - Open Container Manager
   - Go to Container tab
   - Verify "mededbot" is running

### Step 7: Configure LINE Webhook

1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Select your channel
3. Update webhook URL to:
   - Local testing: `http://your-nas-ip:10001/webhook`
   - With DDNS/domain: `https://your-domain.com:10001/webhook`
4. Enable webhooks
5. Verify webhook

## 🔧 Storage Configuration

The deployment automatically uses **disk storage mode** when PORT=10001, storing files in:
- `/volume1/docker/mededbot/tts_audio/` - Text-to-speech audio files
- `/volume1/docker/mededbot/voicemail/` - Voice message files
- `/volume1/docker/mededbot/logs/` - Application logs

## 🛡️ Security Recommendations

### Firewall Configuration

1. Open **Control Panel** → **Security** → **Firewall**
2. Create new rule:
   - Port: 10001
   - Protocol: TCP
   - Source IP: Your local network (e.g., 192.168.1.0/24)
   - Action: Allow

### Reverse Proxy (Optional)

For HTTPS access:

1. **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
2. Create new rule:
   - Source: `https://bot.yourdomain.com:443`
   - Destination: `http://localhost:10001`
   - Enable HSTS and HTTP/2

## 🔄 Maintenance

### View Logs
```bash
# Container logs
sudo docker logs mededbot

# Application logs
ls -la /volume1/docker/mededbot/logs/
```

### Update Application
```bash
cd /volume1/docker/mededbot
git pull  # If using git
sudo docker-compose -f docker-compose.synology.yml up -d --build
```

### Cleanup Old Files
```bash
# Run the cleanup script (removes TTS files older than 7 days)
sudo /volume1/docker/mededbot/cleanup_old_audio.sh
```

### Backup Data
```bash
# Run the backup script
sudo /volume1/docker/mededbot/backup_data.sh
```

## 📊 Resource Monitoring

Monitor in Container Manager:
- CPU usage (should be < 20% average)
- Memory usage (should be < 500MB)
- Network I/O

## 🐛 Troubleshooting

### Container Won't Start
```bash
# Check logs
sudo docker logs mededbot

# Verify permissions
ls -la /volume1/docker/mededbot/

# Test database connection
sudo docker exec mededbot python -c "import os; print(os.getenv('DATABASE_URL'))"
```

### Permission Errors
```bash
# Fix ownership
sudo chown -R 1000:1000 /volume1/docker/mededbot/
sudo chmod 775 /volume1/docker/mededbot/{tts_audio,voicemail,logs}
```

### Port Already in Use
```bash
# Check what's using port 10001
sudo netstat -tulpn | grep 10001

# Stop conflicting service or change port in .env and docker-compose
```

### Can't Access from Network
1. Check firewall rules
2. Verify BASE_URL in .env
3. Ensure container is running: `docker ps`

## 📝 Quick Commands Reference

```bash
# Start
sudo docker-compose -f docker-compose.synology.yml up -d

# Stop
sudo docker-compose -f docker-compose.synology.yml down

# Restart
sudo docker-compose -f docker-compose.synology.yml restart

# View logs
sudo docker-compose -f docker-compose.synology.yml logs -f

# Update and rebuild
git pull
sudo docker-compose -f docker-compose.synology.yml up -d --build

# Shell access
sudo docker exec -it mededbot sh
```

## ✅ Success Checklist

- [ ] Container shows "Running" in Container Manager
- [ ] Health check returns success at `http://nas-ip:10001/`
- [ ] No permission errors in logs
- [ ] LINE webhook verified and working
- [ ] Test message receives response
- [ ] Audio files created in `/volume1/docker/mededbot/tts_audio/`
- [ ] Database operations show "✅ [DB]" in logs

## 🆘 Support

If you encounter issues:
1. Check container logs first
2. Verify all environment variables are set
3. Ensure proper file permissions (UID/GID 1000)
4. Test each component individually

Remember: The key for Synology deployment is proper permissions. When in doubt, check ownership and permissions!