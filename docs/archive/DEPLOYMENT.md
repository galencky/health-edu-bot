# MedEdBot Deployment Guide

## 🐳 Docker Deployment

### Building the Image

```bash
# Build the Docker image
docker build -t mededbot:latest .

# Or with specific tag
docker build -t mededbot:v1.0.0 .
```

### Running with Docker

```bash
# Run with environment variables
docker run -d \
  --name mededbot \
  -p 10001:10001 \
  --restart unless-stopped \
  -e LINE_CHANNEL_ACCESS_TOKEN=your_token \
  -e LINE_CHANNEL_SECRET=your_secret \
  -e GEMINI_API_KEY=your_key \
  -e GMAIL_ADDRESS=your_email \
  -e GMAIL_APP_PASSWORD=your_password \
  -e GOOGLE_DRIVE_FOLDER_ID=your_folder_id \
  -e GOOGLE_CREDS_B64=your_base64_creds \
  -e BASE_URL=https://your-domain.com \
  -e LOG_LEVEL=info \
  mededbot:latest

# Or run with .env file (Windows PowerShell)
docker run -d `
  --name mededbot `
  -p 10001:10001 `
  --restart unless-stopped `
  --env-file .env `
  -v ${PWD}/data/tts_audio:/app/tts_audio `
  -v ${PWD}/data/voicemail:/app/voicemail `
  mededbot:latest

# Or run with .env file (Linux/WSL)
docker run -d \
  --name mededbot \
  -p 10001:10001 \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data/tts_audio:/app/tts_audio \
  -v $(pwd)/data/voicemail:/app/voicemail \
  mededbot:latest
```

### Using Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Update and restart
docker-compose pull && docker-compose up -d
```

---

## 🏠 Synology NAS Container Manager Deployment

### Method 1: Using Container Manager GUI

#### Step 1: Prepare Files
1. Upload project files to your Synology NAS
2. Create folder structure:
   ```
   /docker/mededbot/
   ├── Dockerfile
   ├── docker-compose.yml
   ├── requirements.txt
   ├── main.py
   ├── .env (with your credentials)
   └── ... (other project files)
   ```

#### Step 2: Container Manager Setup
1. Open **Container Manager** in DSM
2. Go to **Project** tab
3. Click **Create**
4. Choose **Create docker-compose.yml**

#### Step 3: Configure Project
1. **Project Name**: `mededbot`
2. **Path**: `/docker/mededbot`
3. **Source**: Select `docker-compose.yml`
4. Review configuration and click **Next**

#### Step 4: Environment Variables
Configure in the **Environment** tab:
```
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_CHANNEL_SECRET=your_line_secret
GEMINI_API_KEY=your_gemini_key
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_password
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_CREDS_B64=your_base64_encoded_service_account
BASE_URL=https://your-domain.com
```

#### Step 5: Port Configuration
- **Container Port**: 10001
- **Local Port**: 10001 (or any available port)
- **Type**: TCP

#### Step 6: Volume Mapping
- `/docker/mededbot/data/tts_audio` → `/app/tts_audio`
- `/docker/mededbot/data/voicemail` → `/app/voicemail`
- `/docker/mededbot/data/logs` → `/app/logs`

### Method 2: Using Docker Registry

#### Step 1: Push to Registry (if using external registry)
```bash
# Tag for your registry
docker tag mededbot:latest your-registry.com/mededbot:latest

# Push to registry
docker push your-registry.com/mededbot:latest
```

#### Step 2: Pull in Synology
1. **Container Manager** → **Registry**
2. Search for your image
3. Download the image
4. Create container with same configuration as above

### Method 3: Using SSH (Advanced)

```bash
# SSH into your Synology NAS
ssh admin@your-nas-ip

# Navigate to docker directory
cd /volume1/docker/mededbot

# Build and run
sudo docker build -t mededbot .
sudo docker run -d \
  --name mededbot \
  -p 10001:10001 \
  --restart unless-stopped \
  --env-file .env \
  mededbot
```

---

## 🌐 Network Configuration

### Local Development (Windows with WSL)
When developing locally on Windows with WSL:
1. **Your machine IP**: 192.168.0.109 (Wi-Fi adapter)
2. **WSL IP**: 172.19.96.1 (WSL Hyper-V adapter)
3. **Docker network**: 172.20.0.0/16 (custom bridge)

Configure BASE_URL in .env:
```bash
# For local testing
BASE_URL=http://192.168.0.109:10001

# For production
BASE_URL=https://your-domain.com
```

### Port Forwarding
For external access (LINE webhooks), configure your router:
1. **External Port**: 443 (HTTPS) or 80 (HTTP)
2. **Internal Port**: 10001
3. **Protocol**: TCP
4. **Destination**: Synology NAS IP

### Reverse Proxy (Recommended)
Configure in Synology **Application Portal**:
1. **Create Reverse Proxy**
2. **Source**:
   - Protocol: HTTPS
   - Hostname: your-domain.com
   - Port: 443
3. **Destination**:
   - Protocol: HTTP
   - Hostname: localhost
   - Port: 10001

### SSL Certificate
1. **Control Panel** → **Security** → **Certificate**
2. Add/Import SSL certificate for your domain
3. Assign to reverse proxy

---

## 📊 Monitoring & Maintenance

### Health Checks
The container includes built-in health checks:
```bash
# Check container health
docker ps
# HEALTHY status indicates everything is working

# Manual health check
curl http://your-nas-ip:10001/ping
```

### Log Management
```bash
# View container logs
docker logs mededbot

# View real-time logs
docker logs -f mededbot

# Limit log size (in docker-compose.yml)
logging:
  options:
    max-size: "10m"
    max-file: "3"
```

### Resource Monitoring
In Synology **Resource Monitor**:
- Monitor CPU usage
- Monitor memory usage
- Monitor network traffic

### Backup Strategy
1. **Configuration Backup**:
   - Backup `/docker/mededbot/` folder
   - Include `.env` file (securely)

2. **Data Backup**:
   - Backup `data/` volumes
   - Include TTS audio and voicemail files

---

## 🔧 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker logs mededbot

# Common causes:
# 1. Missing environment variables
# 2. Port already in use
# 3. Invalid .env file format
```

#### LINE Webhook Fails
1. Verify `BASE_URL` is accessible from internet
2. Check SSL certificate is valid
3. Ensure port forwarding is configured
4. Test with: `curl https://your-domain.com/ping`

#### TTS Audio Not Working
1. Verify `BASE_URL` points to your public domain
2. Check static files are being served:
   `curl https://your-domain.com/static/test.wav`
3. Ensure ffmpeg is installed (included in Docker image)

#### Google Services Failing
1. Verify `GOOGLE_CREDS_B64` is correctly encoded:
   ```bash
   echo "your_base64_string" | base64 -d | jq .
   ```
2. Check Google Cloud service account permissions
3. Verify Drive folder ID is correct

### Performance Tuning

#### Resource Limits
Adjust in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 2G        # Increase for heavy usage
      cpus: '1.0'       # Increase for better performance
```

#### Scaling for High Load
```bash
# Run multiple instances with load balancer
docker-compose up --scale mededbot=3
```

---

## 🔒 Security Considerations

### Environment Variables
- Never commit `.env` file to version control
- Use Synology's secret management when possible
- Rotate API keys regularly

### Network Security
- Use HTTPS for all external communication
- Restrict access to management ports
- Keep Synology DSM updated

### Container Security
- Container runs as non-root user
- Minimal attack surface with slim base image
- Regular updates of base image and dependencies

---

## 📈 Scaling & High Availability

### Load Balancing
For high-traffic deployments:
1. Run multiple container instances
2. Use nginx or HAProxy for load balancing
3. Implement session affinity if needed

### Database Migration
For persistent sessions:
1. Implement Redis for session storage
2. Update `session_manager.py` to use Redis
3. Add Redis container to docker-compose.yml

### Monitoring Setup
Recommended monitoring stack:
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards
- **AlertManager**: Alerting

---

*For additional support, contact: galen147258369@gmail.com*