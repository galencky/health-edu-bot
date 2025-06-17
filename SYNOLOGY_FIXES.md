# Synology NAS Deployment Fixes Applied

Based on ChatGPT o3's debugging advice, the following critical fixes have been applied:

## 1. Critical Runtime Hazards Fixed ✅

### 1.1 No duplicate modules found
- Verified only one copy of each module exists
- No duplicate `session_manager.py` or other files

### 1.2 Fixed ThreadPoolExecutor explosion in gemini_service.py
- Changed from creating new executor on every request to using a global executor
- Fixed thread-local storage issue by using process-wide storage with lock
- Limited to 4 worker threads: `_gemini_executor = ThreadPoolExecutor(max_workers=4)`

### 1.3 Fixed async/sync mixing in /chat endpoint
- Changed from async function with thread pool to pure sync function
- Removed unnecessary `await loop.run_in_executor()` call

### 1.4 Fixed Python 3.9/3.10 compatibility
- Replaced `asyncio.timeout()` with `asyncio.wait_for()` in webhook.py
- Now compatible with older Python versions on Synology

### 1.5 Fixed mandatory BASE_URL requirement
- TTS service now handles missing BASE_URL gracefully
- Falls back to relative URLs instead of crashing

## 2. Performance/Stability Fixes ✅

### 2.1 Fixed unbounded event loop creation
- Changed from creating new event loops to using `asyncio.run()`
- Properly manages event loop lifecycle

### 2.2 No duplicate periodic tasks found
- Only one session cleanup task
- Added TTS file cleanup task for disk storage

### 2.3 Thread explosion prevention
- Global executors with limited workers
- Bounded thread pools for logging and Gemini API

### 2.4 Blocking disk IO (partially addressed)
- Identified issue in audio file writing
- Left as-is to avoid breaking working system

### 2.5 TTS file cleanup restored
- Added periodic cleanup every hour
- Removes files older than 24 hours
- Enforces 500MB directory size limit

## 3. Configuration Fixes ✅

### 3.1 Clock drift - Not addressed (Synology admin task)

### 3.2 Google credentials - Uses environment variable

### 3.3 Port configuration
- Changed default from 10001 to 8080
- Uses PORT environment variable

### 3.4 load_dotenv() - Left as-is (working system)

## Deployment Instructions

1. Use the simplified Dockerfile:
```bash
docker build -f Dockerfile.synology-simple -t mededbot .
docker run -d --name mededbot -p 10001:8080 --env-file .env mededbot
```

2. Or use docker-compose:
```bash
docker-compose -f docker-compose.synology-simple.yml up -d
```

3. Check logs:
```bash
docker logs -f mededbot
```

## Key Changes Summary

- **Thread Safety**: Global executors prevent thread explosion
- **Python Compatibility**: Works with Python 3.9+
- **Resource Management**: Proper cleanup tasks
- **Error Handling**: Graceful fallbacks for missing config
- **Memory Efficiency**: Bounded thread pools

The system should now run stably on Synology NAS without OCI runtime errors or resource exhaustion.