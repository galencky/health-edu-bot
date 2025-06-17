# Synology NAS Deployment Guide

## IMPORTANT: Making Logs Visible in Container Manager

**Problem**: Container Manager's Log tab stays empty even though `docker logs` works.

**Solution**: 
1. **NEVER use TTY mode** - Set `tty: false` and `stdin_open: false` in docker-compose
2. **Enable Python unbuffered mode** - Set `PYTHONUNBUFFERED=1` 
3. **Use default log driver** - Don't change from `json-file`

The docker-compose files have been configured correctly for this.

## OCI Runtime Error Troubleshooting

If you're getting "OCI runtime exec failed" error, try these solutions:

### Solution 1: Use Simple Dockerfile (Recommended)

```bash
# Build with the simple Dockerfile
docker build -f Dockerfile.synology-simple -t mededbot-simple .

# Run directly without docker-compose
docker run -d \
  --name mededbot \
  -p 10001:8080 \
  --env-file .env \
  -e PORT=8080 \
  -e PYTHONUNBUFFERED=1 \
  -v $(pwd)/data/tts_audio:/app/tts_audio \
  -v $(pwd)/data/voicemail:/app/voicemail \
  -v $(pwd)/data/logs:/app/logs \
  mededbot-simple
```

### Solution 2: Use Container Manager GUI

1. In Synology Container Manager, create a new container
2. Use image: `python:3.11`
3. Set these environment variables:
   - `PYTHONUNBUFFERED=1`
   - `PORT=8080`
   - Plus all your .env variables
4. Mount volumes:
   - `/docker/mededbot/app` → `/app`
   - `/docker/mededbot/data` → `/app/data`
5. Set command: `python -m uvicorn main:app --host 0.0.0.0 --port 8080`

### Solution 3: Debug Container

First, test if the container can start:

```bash
# Test with shell
docker run -it --rm \
  --env-file .env \
  -v $(pwd):/app \
  python:3.11 \
  /bin/bash

# Inside container, test the app
cd /app
pip install -r requirements.txt
python test-container.py
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

### Solution 4: Use Direct Python Execution

Create container with this command:
```bash
docker run -d \
  --name mededbot \
  -p 10001:8080 \
  --env-file .env \
  -e PYTHONUNBUFFERED=1 \
  -v $(pwd):/app \
  -w /app \
  python:3.11 \
  sh -c "pip install -r requirements.txt && python -m uvicorn main:app --host 0.0.0.0 --port 8080"
```

### Common Issues on Synology

1. **Permissions**: Synology runs containers with specific UIDs
   ```bash
   # Fix permissions
   sudo chown -R 1000:1000 ./data
   ```

2. **Memory limits**: Synology may have strict memory limits
   - Remove memory limits from docker-compose
   - Use `--memory=1g` flag if needed

3. **Shell issues**: Synology's Docker version may have shell compatibility issues
   - Use `python` directly instead of `sh` or `bash`
   - Avoid complex shell scripts

4. **Network mode**: Try host network mode
   ```bash
   docker run --network host ...
   ```

### Minimal Working Example

If all else fails, use this minimal setup:

1. Create `run.sh` in your Synology shared folder:
```bash
#!/bin/sh
cd /volume1/docker/mededbot
docker stop mededbot 2>/dev/null
docker rm mededbot 2>/dev/null
docker run -d \
  --name mededbot \
  --network host \
  --env-file .env \
  -v $(pwd):/app \
  -w /app \
  python:3.11 \
  python main.py
```

2. Make it executable: `chmod +x run.sh`
3. Run it: `./run.sh`

### Checking Logs

```bash
# View container logs
docker logs mededbot

# Follow logs
docker logs -f mededbot

# Check Synology system logs
sudo cat /var/log/messages | grep docker
```

### Using Synology Task Scheduler

If Container Manager fails, use Task Scheduler:

1. Create a scheduled task (User-defined script)
2. Run as root
3. Script:
```bash
cd /volume1/docker/mededbot
/usr/local/bin/python3 -m pip install -r requirements.txt
/usr/local/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 10001
```

This bypasses Docker entirely and runs the app directly on Synology.