# 🚀 Synology NAS Deployment Guide for MedEdBot V4

This guide will help you deploy MedEdBot V4 on your Synology NAS using Docker/Container Manager with external port 10002.

## 📋 Prerequisites

- Synology NAS with DSM 7.0 or later
- Container Manager installed from Package Center
- SSH access enabled
- At least 1GB free RAM
- Port 10002 available (external)

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
   # Note: The script will create directories in /volume1/docker/mededbot-v4/
   sudo curl -L https://raw.githubusercontent.com/yourusername/mededbot/main/synology_setup.sh -o /tmp/setup.sh
   sudo bash /tmp/setup.sh
   ```

   This script will:
   - Create directories in `/volume1/docker/mededbot-v4/`
   - Set proper permissions (UID/GID 1000)
   - Create .env template with PORT=10001 (internal)
   - Set up maintenance scripts

### Step 3: Copy Project Files

1. **Using File Station (GUI):**
   - Open File Station
   - Navigate to `/docker/mededbot-v4/`
   - Upload all project files including:
     - All Python files (*.py)
     - requirements.txt
     - Dockerfile
     - docker-compose.synology.yml
     - .env (configured)
     - credentials.json (if using file-based auth)

2. **Using SCP (Command Line):**
   ```bash
   # From your local machine
   scp -r /path/to/mededbot/* admin@nas-ip:/volume1/docker/mededbot-v4/
   ```

### Step 4: Configure Environment

1. **Edit the .env file:**
   ```bash
   sudo nano /volume1/docker/mededbot-v4/.env
   ```

2. **Required configurations:**
   - `DATABASE_URL` - Your PostgreSQL connection string
   - `LINE_CHANNEL_ACCESS_TOKEN` - From LINE Developers Console
   - `LINE_CHANNEL_SECRET` - From LINE Developers Console
   - `GEMINI_API_KEY` - From Google AI Studio
   - `GMAIL_ADDRESS` - Your Gmail address
   - `GMAIL_APP_PASSWORD` - Gmail app-specific password
   - `BASE_URL` - Set to `http://your-nas-ip:10002` (external port!)
   - `PORT=10001` - Keep this as 10001 (internal port for disk storage)

3. **Optional Google Drive setup:**
   - `GOOGLE_DRIVE_FOLDER_ID` - Your Drive folder ID
   - If using credentials file:
     - Place `credentials.json` in `/volume1/docker/mededbot-v4/credentials/`
     - Remove or comment out `GOOGLE_CREDS_B64` in .env

### Step 5: Build and Run

1. **Navigate to project directory:**
   ```bash
   cd /volume1/docker/mededbot-v4
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

1. **Test health endpoint (using external port):**
   ```bash
   curl http://localhost:10002/
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
   - Check port mapping shows 10002 → 10001

### Step 7: Configure LINE Webhook

1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Select your channel
3. Update webhook URL to:
   - Local testing: `http://your-nas-ip:10002/webhook`
   - With DDNS/domain: `https://your-domain.com:10002/webhook`
4. Enable webhooks
5. Verify webhook

## 🔧 Port Configuration Details

- **External Port**: 10002 (what users/LINE accesses)
- **Internal Port**: 10001 (keeps disk storage mode active)
- **Why?**: Internal PORT=10001 ensures disk storage mode is used
- **Storage Location**: `/volume1/docker/mededbot-v4/`

## 🛡️ Security Recommendations

### Firewall Configuration

1. Open **Control Panel** → **Security** → **Firewall**
2. Create new rule:
   - Port: 10002 (external port)
   - Protocol: TCP
   - Source IP: Your local network (e.g., 192.168.1.0/24)
   - Action: Allow

### Reverse Proxy (Optional)

For HTTPS access:

1. **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
2. Create new rule:
   - Source: `https://bot.yourdomain.com:443`
   - Destination: `http://localhost:10002`
   - Enable HSTS and HTTP/2

## 🔄 Maintenance

### View Logs
```bash
# Container logs
sudo docker logs mededbot

# Application logs
ls -la /volume1/docker/mededbot-v4/logs/
```

### Update Application
```bash
cd /volume1/docker/mededbot-v4
# Copy new files or git pull
sudo docker-compose -f docker-compose.synology.yml up -d --build
```

### Cleanup Old Files
```bash
# Run the cleanup script (removes TTS files older than 7 days)
sudo /volume1/docker/mededbot-v4/cleanup_old_audio.sh
```

### Backup Data
```bash
# Run the backup script
sudo /volume1/docker/mededbot-v4/backup_data.sh
```

## 📊 Storage Locations

All data is stored in disk mode at:
- **TTS Audio**: `/volume1/docker/mededbot-v4/tts_audio/`
- **Voicemail**: `/volume1/docker/mededbot-v4/voicemail/`
- **Logs**: `/volume1/docker/mededbot-v4/logs/`
- **Config**: `/volume1/docker/mededbot-v4/.env`
- **Credentials**: `/volume1/docker/mededbot-v4/credentials/`

## 🐛 Troubleshooting

### Container Won't Start
```bash
# Check logs
sudo docker logs mededbot

# Verify permissions
ls -la /volume1/docker/mededbot-v4/

# Check port mapping
sudo docker ps | grep mededbot
```

### Permission Errors
```bash
# Fix ownership
sudo chown -R 1000:1000 /volume1/docker/mededbot-v4/
sudo chmod 775 /volume1/docker/mededbot-v4/{tts_audio,voicemail,logs}
```

### Port Conflicts
```bash
# Check what's using port 10002
sudo netstat -tulpn | grep 10002

# If port 10001 is in use (by old version), that's OK
# The container uses 10001 internally, 10002 externally
```

### Can't Access from Network
1. Check firewall rules for port 10002
2. Verify BASE_URL in .env uses port 10002
3. Ensure container port mapping: 10002→10001

## 📝 Quick Commands Reference

```bash
# Start
cd /volume1/docker/mededbot-v4
sudo docker-compose -f docker-compose.synology.yml up -d

# Stop
sudo docker-compose -f docker-compose.synology.yml down

# Restart
sudo docker-compose -f docker-compose.synology.yml restart

# View logs
sudo docker-compose -f docker-compose.synology.yml logs -f

# Update and rebuild
sudo docker-compose -f docker-compose.synology.yml up -d --build

# Shell access
sudo docker exec -it mededbot sh
```

## ✅ Success Checklist

- [ ] Container shows "Running" in Container Manager
- [ ] Port mapping shows 10002 → 10001
- [ ] Health check returns success at `http://nas-ip:10002/`
- [ ] No permission errors in logs
- [ ] LINE webhook verified at port 10002
- [ ] Test message receives response
- [ ] Audio files created in `/volume1/docker/mededbot-v4/tts_audio/`
- [ ] Database operations show "✅ [DB]" in logs

## 🆘 Important Notes

1. **Internal PORT must stay 10001** in .env to maintain disk storage mode
2. **External access uses port 10002** for all services
3. **BASE_URL must use port 10002** for correct audio file serving
4. **Old service on port 10001** remains unaffected

Remember: The key is the port mapping - external 10002 maps to internal 10001, keeping disk storage active!