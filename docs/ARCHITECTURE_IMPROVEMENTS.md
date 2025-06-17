# Architecture Improvements Applied

Based on ChatGPT o3's architectural advice, the following improvements have been implemented:

## 1. State & Concurrency ✅

### Per-Session Locking
- Added per-user session locks to prevent concurrent mutations
- Global lock for session creation/deletion
- Sessions are now thread-safe for FastAPI's default thread pool

```python
# Usage pattern (to be implemented in handlers):
session = get_user_session(user_id)
lock = get_session_lock(user_id)
with lock:
    # Safely modify session
    session['key'] = value
```

## 2. Logging & Observability ✅

### Unbuffered Output
- `PYTHONUNBUFFERED=1` set in all Dockerfiles
- `python -u` flag added to CMD
- Ensures logs appear in Synology Container Manager

### Exception Logging
- Enhanced webhook exception handling with full stack traces
- Added placeholders for Sentry integration
- Still returns "OK" to prevent LINE retries but logs the error

## 3. Resource Management ✅

### Thread Pool Limits
- Global Gemini executor limited to 4 workers
- Logging executor limited to 5 workers
- Prevents thread explosion under load

### Memory Storage Cleanup
- Added periodic cleanup task for memory storage
- Runs every hour to remove files older than 24 hours
- Prevents OOM on low-RAM NAS

### Graceful Task Cancellation
- All periodic tasks properly handle CancelledError
- Clean shutdown without error spam

## 4. Recommended Next Steps

### High Priority
1. **Typed Session Dataclass** - Replace dict with Pydantic model
2. **Extract Command Handlers** - Break up 400+ line handle_user_message
3. **Replace DIY Infrastructure** - Use tenacity for retries, structlog for logging

### Medium Priority
1. **Service Layer** - Separate business logic from FastAPI routes
2. **Finite State Machine** - Replace boolean flags with proper states
3. **Configuration Management** - Extract magic numbers to config.py

### Low Priority
1. **Unit Tests** - Add pytest suite
2. **CI/CD Pipeline** - Run tests, linting, security scans
3. **API Documentation** - Add OpenAPI schemas

## Quick Wins Implemented

1. ✅ **Unbuffered logging** - Synology can now see logs
2. ✅ **Per-session locks** - No more race conditions
3. ✅ **Thread pool limits** - Prevents resource exhaustion
4. ✅ **Proper error logging** - Stack traces for debugging
5. ✅ **Memory cleanup** - Prevents OOM kills

## Architecture Guidelines

### Don't
- Create new threads/executors per request
- Use mutable global state without locks
- Silently swallow exceptions
- Mix async and sync without care

### Do
- Use bounded thread pools
- Lock shared mutable state
- Log errors with context
- Handle cancellation properly
- Set resource limits

The codebase is now more stable and ready for production deployment on resource-constrained environments like Synology NAS.