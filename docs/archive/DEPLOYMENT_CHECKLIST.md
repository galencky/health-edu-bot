# MedEdBot Synology NAS Docker Deployment Checklist

## ✅ Pre-Deployment Checklist

### 📋 System Requirements
- [ ] Synology NAS with DSM 7.0+
- [ ] Docker package installed
- [ ] At least 1GB RAM available
- [ ] 2GB+ free storage space
- [ ] Network access to external APIs

### 🔧 Environment Setup
- [ ] `.env` file created with all required variables
- [ ] Database URL configured (Neon PostgreSQL)
- [ ] LINE Bot credentials configured
- [ ] Google AI API key configured
- [ ] Google Drive credentials configured
- [ ] Gmail SMTP credentials configured
- [ ] BASE_URL configured for your domain/IP

### 📁 Directory Structure
- [ ] `/volume1/docker/mededbot/` created
- [ ] `/volume1/docker/mededbot/source/` contains project files
- [ ] `/volume1/docker/mededbot/tts_audio/` created (755 permissions)
- [ ] `/volume1/docker/mededbot/voicemail/` created (755 permissions)
- [ ] `/volume1/docker/mededbot/logs/` created (755 permissions)

## 🐳 Docker Deployment Checklist

### 🏗️ Image Building
- [ ] All project files uploaded to Synology
- [ ] Dockerfile reviewed and appropriate for Alpine Linux
- [ ] requirements.txt includes all dependencies
- [ ] .dockerignore excludes unnecessary files
- [ ] Docker image builds successfully

### 📦 Container Configuration
- [ ] Container name: `mededbot`
- [ ] Port mapping: `10001:10001`
- [ ] Volume mounts configured:
  - [ ] `tts_audio` → `/app/tts_audio`
  - [ ] `voicemail` → `/app/voicemail`
  - [ ] `logs` → `/app/logs`
  - [ ] `.env` → `/app/.env` (read-only)
- [ ] Environment variables loaded
- [ ] Resource limits set appropriately
- [ ] Auto-restart enabled
- [ ] Health check configured

### 🔐 Security Configuration
- [ ] Non-root user configured (appuser)
- [ ] No new privileges flag set
- [ ] Minimal dependencies installed
- [ ] Sensitive data in environment variables only

## 🌐 Network Configuration Checklist

### 🔌 Port Configuration
- [ ] Container port 10001 exposed
- [ ] Host port mapping configured
- [ ] Synology firewall allows port 10001 (if needed)
- [ ] Router port forwarding configured (if external access needed)

### 🌍 External Access (Optional)
- [ ] Domain name configured
- [ ] SSL certificate configured
- [ ] LINE webhook URL updated
- [ ] BASE_URL updated to match external URL

## 🧪 Testing Checklist

### 🏥 Health Checks
- [ ] Container starts successfully
- [ ] Health check endpoint responds: `GET /`
- [ ] Ping endpoint responds: `GET /ping`
- [ ] Container logs show no errors

### 🤖 Bot Functionality
- [ ] Database connection successful
- [ ] LINE webhook receiving messages
- [ ] Gemini AI responses working
- [ ] TTS generation working
- [ ] Google Drive uploads working
- [ ] Email notifications working (if configured)

### 📊 Database Testing
- [ ] Database tables created successfully
- [ ] Chat logs being written
- [ ] TTS logs being written
- [ ] Voicemail logs being written (if applicable)
- [ ] Database queries working from `view_logs.py`

### 📱 LINE Integration Testing
- [ ] Webhook URL configured in LINE Developer Console
- [ ] Bot responds to text messages
- [ ] Bot responds to voice messages
- [ ] Quick reply buttons working
- [ ] Flex messages displaying correctly

## 📈 Monitoring Setup Checklist

### 📊 Container Monitoring
- [ ] Container Manager shows healthy status
- [ ] Resource usage within limits
- [ ] Log rotation configured (10MB max, 3 files)
- [ ] Health check status green

### 🔍 Application Monitoring
- [ ] Application logs accessible in `/volume1/docker/mededbot/logs/`
- [ ] Database logging visible in Neon dashboard
- [ ] Google Drive folder receiving files
- [ ] Error notifications configured (if desired)

## 🔧 Maintenance Checklist

### 🔄 Regular Maintenance
- [ ] Container auto-restart configured
- [ ] Log file rotation working
- [ ] Database connection pool healthy
- [ ] Disk space monitoring setup

### 🆙 Update Process
- [ ] Image rebuild process documented
- [ ] Data backup strategy defined
- [ ] Rollback plan documented
- [ ] Environment variable management process

## 🚨 Troubleshooting Checklist

### 📋 Common Issues
- [ ] Container won't start → Check logs and environment variables
- [ ] Database connection fails → Verify DATABASE_URL and network
- [ ] LINE webhook fails → Check webhook URL and certificates
- [ ] Google API fails → Verify credentials and quotas
- [ ] Files not uploading → Check Google Drive permissions
- [ ] Out of memory → Increase memory limit or optimize

### 🔍 Debugging Tools
- [ ] Container logs: `docker logs mededbot`
- [ ] Interactive shell: `docker exec -it mededbot sh`
- [ ] Database test: `python test_logging_visibility.py`
- [ ] Audio upload test: `python test_audio_upload.py`
- [ ] Log viewer: `python view_logs.py`

## 📚 Documentation Checklist

### 📖 Documentation Complete
- [ ] Deployment guide available
- [ ] Environment variables documented
- [ ] Troubleshooting guide available
- [ ] API endpoints documented
- [ ] Database schema documented

### 🔒 Security Documentation
- [ ] Security considerations documented
- [ ] Access control configured
- [ ] Credential management process documented
- [ ] Backup and recovery procedures documented

## ✅ Post-Deployment Validation

### 🎯 Final Tests
- [ ] Complete end-to-end test with real LINE messages
- [ ] Voice message processing test
- [ ] TTS generation and playback test
- [ ] Database query test
- [ ] Google Drive file upload test
- [ ] Email notification test (if configured)

### 📈 Performance Validation
- [ ] Response time under 5 seconds for text messages
- [ ] TTS generation under 10 seconds
- [ ] Memory usage stable under 1GB
- [ ] CPU usage reasonable
- [ ] No memory leaks detected

### 🔐 Security Validation
- [ ] No sensitive data in logs
- [ ] Container running as non-root user
- [ ] Network access properly restricted
- [ ] Credentials properly secured

---

## 🎉 Deployment Complete!

Once all items are checked, your MedEdBot should be successfully deployed on Synology NAS with:

- ✅ Automatic restarts and health monitoring
- ✅ Persistent data storage
- ✅ Secure container configuration
- ✅ Complete logging and monitoring
- ✅ Scalable resource management

### 📞 Support
If any items fail, check the `SYNOLOGY_DEPLOYMENT.md` guide for detailed troubleshooting steps.