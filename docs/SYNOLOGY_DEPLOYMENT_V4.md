# 🚀 Synology NAS Deployment Guide for MedEdBot V4 (Memory Storage)

This guide will help you deploy MedEdBot V4 on your Synology NAS using Docker/Container Manager with memory storage mode (like Render) and Google Drive backup.

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
   sudo curl -L https://raw.githubusercontent.com/yourusername/mededbot/main/scripts/synology_setup.sh -o /tmp/setup.sh
   sudo bash /tmp/setup.sh
   ```

   This script will:
   - Create directories in `/volume1/docker/mededbot-v4/`
   - Set proper permissions (UID/GID 1000)
   - Create .env template with PORT=8080 (for memory storage)
   - Set up backup scripts (no cleanup needed for memory storage)

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
   - `PORT=8080` - Keep this as 8080 (internal port for memory storage)
   - `USE_MEMORY_STORAGE=true` - Explicitly enable memory storage

3. **Required Google Drive setup (for memory storage backup):**
   - `GOOGLE_DRIVE_FOLDER_ID` - Your Drive folder ID (REQUIRED)
   - Place `service-account.json` in `/volume1/docker/mededbot-v4/credentials/`
   - The docker-compose already mounts this file

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

## 🔧 Configuration Details

- **External Port**: 10002 (what users/LINE accesses)
- **Internal Port**: 8080 (enables memory storage mode)
- **Storage Mode**: Memory (RAM) with Google Drive backup
- **Memory Limits**: 100 files max, 24-hour TTL
- **Google Drive**: All files automatically backed up

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

### Memory Storage Notes
```bash
# No cleanup needed - files are in memory with automatic TTL
# All files are backed up to Google Drive automatically
```

### Backup Data
```bash
# Run the backup script
sudo /volume1/docker/mededbot-v4/backup_data.sh
```

## 📊 Storage Configuration

Memory storage mode (like Render):
- **TTS Audio**: Stored in RAM, backed up to Google Drive
- **Voicemail**: Stored in RAM, backed up to Google Drive  
- **Logs**: Optional persistent mount at `/volume1/docker/mededbot-v4/logs/`
- **Config**: `/volume1/docker/mededbot-v4/.env`
- **Credentials**: `/volume1/docker/mededbot-v4/credentials/service-account.json`

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
# Fix ownership for config files
sudo chown -R 1000:1000 /volume1/docker/mededbot-v4/
sudo chmod 755 /volume1/docker/mededbot-v4/credentials
sudo chmod 644 /volume1/docker/mededbot-v4/credentials/service-account.json
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
- [ ] Port mapping shows 10002 → 8080
- [ ] Health check returns success at `http://nas-ip:10002/`
- [ ] Logs show "🧠 Memory storage: True"
- [ ] Logs show "☁️ Drive storage: True" (Google Drive enabled)
- [ ] No permission errors in logs
- [ ] LINE webhook verified at port 10002
- [ ] Test message receives response
- [ ] Files being uploaded to Google Drive
- [ ] Database operations show "✅ [DB]" in logs

## 🆘 Important Notes

1. **Internal PORT must be 8080** in .env to enable memory storage mode
2. **External access uses port 10002** for all services
3. **BASE_URL must use port 10002** for correct audio file serving
4. **Google Drive is REQUIRED** for file backup in memory mode
5. **Memory limits**: 100 files max, 24-hour TTL

Remember: Memory storage mode means no local file storage - everything is in RAM and backed up to Google Drive!