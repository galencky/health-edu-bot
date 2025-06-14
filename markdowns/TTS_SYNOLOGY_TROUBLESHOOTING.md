# TTS Audio Playback Troubleshooting for Synology NAS

## Problem
TTS WAV files are successfully generated and uploaded to Google Drive, but LINE shows "cannot play" error when trying to play the audio.

## Root Cause
The issue is almost certainly related to the `BASE_URL` configuration. LINE servers need to fetch the audio file from a publicly accessible URL, but your Synology NAS might not be properly exposed to the internet.

## How TTS Works in MedEdBot

1. **Audio Generation**: Gemini API generates WAV file → saved to `/app/tts_audio/` directory
2. **URL Creation**: `BASE_URL + /static/ + filename` → e.g., `https://your-domain.com/static/user123_1234567890.wav`
3. **LINE Delivery**: URL sent to LINE API → LINE servers fetch the audio file
4. **Playback**: LINE app downloads and plays the audio

## Troubleshooting Steps

### 1. Check BASE_URL Configuration

```bash
# SSH into your Synology and check the current BASE_URL
docker exec mededbot env | grep BASE_URL
```

The `BASE_URL` must be:
- **Publicly accessible** from the internet (not just your local network)
- **HTTPS** for production (LINE requires HTTPS for audio files)
- **Correctly formatted** without trailing slash

### 2. Test Audio File Accessibility

```bash
# Find a recent audio file
docker exec mededbot ls -la /app/tts_audio/

# Test if the file is accessible via the URL
# Replace with your actual BASE_URL and filename
curl -I https://your-domain.com/static/filename.wav
```

You should get a `200 OK` response. If you get `404` or connection timeout, the URL is not accessible.

### 3. Common Issues and Solutions

#### Issue A: Using Internal IP Address
```env
# ❌ Wrong - only works on local network
BASE_URL=http://192.168.1.100:10001

# ✅ Correct - publicly accessible
BASE_URL=https://your-domain.com
```

#### Issue B: Port Not Forwarded
If using your home internet:
1. Configure port forwarding on your router: External Port → Synology IP:10001
2. Use dynamic DNS service (Synology QuickConnect or similar)
3. Update BASE_URL to use your public URL

#### Issue C: HTTPS Not Configured
LINE requires HTTPS in production. Options:
1. **Use Cloudflare Tunnel** (Recommended)
   ```bash
   # Install cloudflared on Synology
   # Create tunnel to expose localhost:10001
   # Update BASE_URL to Cloudflare URL
   ```

2. **Use Synology Reverse Proxy**
   - DSM → Control Panel → Application Portal → Reverse Proxy
   - Create HTTPS proxy rule for port 10001
   - Use Let's Encrypt certificate

3. **Use ngrok for Testing**
   ```bash
   # For testing only
   ngrok http 10001
   # Update BASE_URL with ngrok URL
   ```

### 4. Verify File Permissions

```bash
# Check file permissions
docker exec mededbot ls -la /app/tts_audio/

# Files should be readable
# If not, fix permissions:
docker exec mededbot chmod 644 /app/tts_audio/*.wav
```

### 5. Check Docker Volume Mapping

```bash
# Verify volume is correctly mounted
docker inspect mededbot | grep -A 5 "Mounts"

# Should show:
# /volume1/docker/mededbot/tts_audio:/app/tts_audio
```

### 6. Debug Audio URL Generation

Add temporary logging to see generated URLs:

```python
# In services/tts_service.py, after line 128:
logger.info(f"Generated TTS URL: {url}")
```

Then check logs:
```bash
docker logs mededbot | grep "Generated TTS URL"
```

## Quick Fix Solutions

### Solution 1: Cloudflare Tunnel (Recommended)
1. Sign up for free Cloudflare account
2. Install cloudflared:
   ```bash
   # On Synology via Docker
   docker run -d --name cloudflared \
     --network host \
     cloudflare/cloudflared:latest tunnel \
     --no-autoupdate run --token YOUR_TUNNEL_TOKEN
   ```
3. Update `.env`:
   ```env
   BASE_URL=https://your-tunnel.trycloudflare.com
   ```

### Solution 2: Temporary ngrok (Testing Only)
1. Run ngrok:
   ```bash
   docker run -d --name ngrok \
     --network host \
     ngrok/ngrok:latest http 10001
   ```
2. Get public URL from ngrok dashboard
3. Update BASE_URL with ngrok URL

### Solution 3: Synology QuickConnect
1. Enable QuickConnect in DSM
2. Set up HTTPS certificate
3. Configure reverse proxy for port 10001
4. Update BASE_URL to QuickConnect URL

## Verification

After fixing, test the complete flow:

1. **Send test message in LINE** that triggers TTS
2. **Check logs** for URL generation:
   ```bash
   docker logs -f mededbot
   ```
3. **Test audio URL directly**:
   ```bash
   # Copy URL from logs and test
   curl -I [generated-audio-url]
   ```
4. **Verify in LINE** - audio should now play

## Prevention

To prevent this issue in the future:

1. **Document your BASE_URL** configuration clearly
2. **Set up monitoring** to alert if audio URLs become inaccessible
3. **Use a stable public URL** (domain name, not IP)
4. **Enable HTTPS** for production use
5. **Test audio playback** after any network changes

## Additional Notes

- Audio files must be under 200MB (LINE limitation)
- URLs must be HTTPS in production
- Files are auto-cleaned after 24 hours
- Consider CDN for better global performance