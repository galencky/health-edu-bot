# 🚀 Synology Quick Start Guide - MedEdBot V4

## 📦 What You Need to Do:

1. **Copy entire project folder to:** `/volume1/docker/mededbot-v4/`
   - Include: All files, .env, credentials.json
   - The directory will be created by setup script

2. **SSH into Synology and run:**
   ```bash
   cd /volume1/docker/mededbot-v4
   sudo chmod +x synology_setup.sh
   sudo ./synology_setup.sh
   ```

3. **Verify `.env` file has:**
   ```bash
   PORT=10001  # MUST be 10001 for disk storage
   BASE_URL=http://your-nas-ip:10002  # External port!
   ```

4. **Build and run:**
   ```bash
   cd /volume1/docker/mededbot-v4
   sudo docker-compose -f docker-compose.synology.yml up -d --build
   ```

5. **Verify it's working:**
   ```bash
   curl http://localhost:10002/
   ```

## ✅ Your bot is running on external port 10002 with disk storage!

## 🔍 Key Points:
- **External Port**: 10002 (what you access)
- **Internal Port**: 10001 (keeps disk storage mode)
- **LINE Webhook**: Use port 10002 in URL
- **No conflict** with service on port 10001

## 📁 File Locations:
- **Audio files:** `/volume1/docker/mededbot-v4/tts_audio/`
- **Logs:** `/volume1/docker/mededbot-v4/logs/`
- **Config:** `/volume1/docker/mededbot-v4/.env`

## 🆘 Quick Fixes:
- **Permission error?** `sudo chown -R 1000:1000 /volume1/docker/mededbot-v4/`
- **View logs:** `sudo docker logs -f mededbot`
- **Restart:** `sudo docker-compose -f docker-compose.synology.yml restart`