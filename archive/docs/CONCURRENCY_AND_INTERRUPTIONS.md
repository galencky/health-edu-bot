# MedEdBot Concurrency and User Input Interruptions

## Overview

This document explains how MedEdBot handles concurrent requests, user interruptions, and maintains session isolation in a multi-user environment.

## Architecture for Concurrency

### Thread-Safe Session Management

```python
# Global session store with thread safety
_sessions: Dict[str, UserSession] = {}
_session_lock = threading.RLock()  # Reentrant lock for nested calls

class UserSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.lock = threading.RLock()  # Per-session lock
        self.history: List[Dict] = []
        self.state: Dict[str, Any] = {}
        self.is_processing = False
        self.last_activity = datetime.now()
```

### Session Isolation Guarantees

1. **User Isolation**: Each LINE user has a dedicated session
2. **Thread Safety**: All session access is protected by locks
3. **No Cross-Talk**: Users cannot see or affect other users' sessions
4. **State Consistency**: Session state remains consistent across concurrent requests

## Concurrent Request Scenarios

### Scenario 1: Multiple Users Simultaneously

**Setup**: 3 users send messages at the same time

```
Time    User A              User B              User C
----    ------              ------              ------
T+0     "What is fever?"    "頭痛怎麼辦?"       "糖尿病の症状"
T+1ms   Gets session A      Gets session B      Gets session C
T+2ms   Gemini call A       Gemini call B       Gemini call C
T+3s    Receives reply A    Receives reply B    Receives reply C
```

**Behavior**:
- Each user gets their own session immediately
- All Gemini API calls happen in parallel
- Responses are delivered independently
- No waiting or blocking between users

### Scenario 2: Same User Rapid Messages

**Setup**: Single user sends multiple messages quickly

```
Time    User Action         Bot Processing
----    -----------         --------------
T+0     "Hello"            → Start processing msg1
T+500ms "What is diabetes" → Queue msg2 (msg1 still processing)
T+1s    "Cancel"           → Queue msg3
T+2s    [Waiting]          → Complete msg1, start msg2
T+3s    [Waiting]          → Complete msg2, start msg3
```

**Behavior**:
- Messages are processed sequentially per user
- New messages wait for current processing to complete
- No message loss or duplication
- Order is preserved (FIFO)

### Scenario 3: Audio Message Interruption

**Setup**: User sends audio, then text before transcription completes

```
Time    User Action         Bot Processing
----    -----------         --------------
T+0     [Audio message]    → Download audio
T+1s                       → Start STT transcription
T+2s    "Never mind"       → Queue text message
T+5s                       → Complete transcription
T+5.1s                     → Reply with transcription
T+5.2s                     → Process "Never mind"
```

**Behavior**:
- Audio processing continues even if interrupted
- Text message is queued and processed after
- Both messages get responses
- No partial processing or corruption

## Implementation Details

### 1. Request Queue Management

```python
async def process_message(user_id: str, message: str):
    session = get_user_session(user_id)
    
    # Acquire session lock
    async with session.lock:
        if session.is_processing:
            # Wait for current processing
            await session.processing_complete.wait()
        
        session.is_processing = True
        try:
            # Process the message
            response = await handle_message(message)
            return response
        finally:
            session.is_processing = False
            session.processing_complete.set()
```

### 2. Timeout Handling

```python
REQUEST_TIMEOUT = 30  # seconds

async def process_with_timeout(func, *args):
    try:
        return await asyncio.wait_for(
            func(*args), 
            timeout=REQUEST_TIMEOUT
        )
    except asyncio.TimeoutError:
        return "Processing is taking longer than expected. Please try again."
```

### 3. Graceful Degradation

When system is overloaded:

```python
if get_active_sessions_count() > MAX_CONCURRENT_SESSIONS:
    return "System is busy. Please try again in a moment."

if get_queue_size(user_id) > MAX_QUEUE_PER_USER:
    return "Too many pending requests. Please wait for current processing."
```

## Interruption Handling Strategies

### 1. Command Interruptions

Users can interrupt ongoing processes with commands:

- **"取消"** / **"Cancel"**: Attempts to cancel current operation
- **"返回"** / **"Back"**: Returns to previous menu
- **"主選單"** / **"Main menu"**: Returns to main menu

### 2. Mode Switching

```python
# User in education mode sends medical question
if is_medical_question(message) and session.mode == "education":
    # Gracefully switch modes
    session.mode = "medical"
    return handle_medical_question(message)
```

### 3. Error Recovery

```python
try:
    response = await process_message(message)
except Exception as e:
    # Log error but don't crash session
    log_error(f"Processing error for {user_id}: {e}")
    
    # Recover session state
    session.reset_to_safe_state()
    
    return "An error occurred. Please try again."
```

## Best Practices for Concurrency

### 1. Lock Granularity

- **Session-level locks**: For user state modifications
- **Resource-level locks**: For shared resources (files, connections)
- **No global locks**: Avoid blocking all users

### 2. Async Everything

```python
# Good: Non-blocking I/O
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad: Blocking I/O
def fetch_data():
    return requests.get(url).json()  # Blocks entire thread
```

### 3. Resource Pooling

```python
# Connection pool for database
db_pool = create_pool(
    min_size=10,
    max_size=50,
    max_queries=50000,
    max_inactive_connection_lifetime=300
)

# HTTP client session reuse
http_session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=100)
)
```

## Performance Considerations

### 1. Message Processing Times

- **Text messages**: 1-3 seconds average
- **Audio messages**: 3-10 seconds (includes STT)
- **Email sending**: 2-5 seconds
- **Complex queries**: Up to 30 seconds

### 2. Concurrent User Limits

- **Recommended**: 100 concurrent users
- **Maximum tested**: 500 concurrent users
- **Per-user queue**: Maximum 10 pending messages

### 3. Resource Usage

```python
# Memory per session: ~1MB
# CPU per active request: ~5%
# Network bandwidth: ~10KB per message

# Scaling formula
max_users = available_memory_mb / 1.5
max_concurrent = cpu_cores * 25
```

## Monitoring and Debugging

### 1. Session Metrics

```python
def get_session_metrics():
    return {
        "active_sessions": len(_sessions),
        "processing_sessions": sum(1 for s in _sessions.values() if s.is_processing),
        "queued_messages": sum(s.queue_size for s in _sessions.values()),
        "oldest_session": min(s.created_at for s in _sessions.values())
    }
```

### 2. Debug Logging

```python
logger.debug(f"Session {user_id}: Acquired lock")
logger.debug(f"Session {user_id}: Processing message: {message[:50]}...")
logger.debug(f"Session {user_id}: Released lock, queue size: {queue_size}")
```

### 3. Health Checks

```python
@app.get("/health/concurrency")
async def health_concurrency():
    return {
        "status": "healthy",
        "metrics": get_session_metrics(),
        "warnings": get_concurrency_warnings()
    }
```

## Common Issues and Solutions

### Issue 1: Deadlocks

**Problem**: Two sessions waiting for each other
**Solution**: Always acquire locks in the same order

### Issue 2: Memory Leaks

**Problem**: Sessions not being cleaned up
**Solution**: Automatic session expiry after 30 minutes

### Issue 3: Queue Overflow

**Problem**: Too many pending messages per user
**Solution**: Reject new messages when queue is full

### Issue 4: Timeout Cascades

**Problem**: One slow request causes timeouts for others
**Solution**: Independent timeout per request, circuit breakers

## Testing Concurrency

### Load Testing Script

```python
async def load_test(num_users=100, messages_per_user=5):
    tasks = []
    for i in range(num_users):
        user_id = f"test_user_{i}"
        for j in range(messages_per_user):
            task = send_message(user_id, f"Test message {j}")
            tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    analyze_results(results)
```

### Chaos Testing

1. Random delays in processing
2. Simulated API failures
3. Memory pressure scenarios
4. Network interruptions

## Future Improvements

1. **WebSocket Support**: For real-time bidirectional communication
2. **Message Priority**: Urgent messages processed first
3. **Distributed Sessions**: Redis-backed sessions for scaling
4. **Request Batching**: Combine similar requests for efficiency
5. **Predictive Scaling**: Auto-scale based on usage patterns