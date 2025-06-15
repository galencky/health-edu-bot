# 🔄 MedEdBot Concurrency & Message Handling Behavior

This document explains how MedEdBot handles concurrent requests, message interruptions, and multiple users interacting simultaneously.

## 📊 Overview

MedEdBot uses a **session-based architecture** with thread-safe locks to handle multiple users and concurrent requests. Each user has their own isolated session that prevents cross-contamination of conversations.

## 🔐 Session Management

### User Session Isolation
```python
# Each user gets a unique session based on their LINE user ID
session = get_user_session(user_id)
```

- **Session Key**: Each LINE user has a unique `user_id` that maps to their session
- **Session Storage**: Sessions are stored in a global dictionary with thread-safe access
- **Session Contents**: Each session stores:
  - Conversation history
  - Processing state
  - Temporary data (audio files, etc.)
  - User preferences

### Thread Safety
```python
# Global lock prevents race conditions when accessing sessions
_session_lock = threading.RLock()
```

## 🚦 Concurrent User Behavior

### Scenario 1: Multiple Users Send Requests Simultaneously

**What happens:**
1. User A sends "What is diabetes?"
2. User B sends "Explain hypertension" (at the same time)
3. User C sends "Tell me about vaccines" (at the same time)

**Bot behavior:**
```
Timeline:
T+0ms   : All three requests arrive
T+1ms   : FastAPI creates 3 separate worker threads
T+2ms   : Each thread gets its user's session (with lock)
T+3ms   : All three Gemini API calls start in parallel
T+1-3s  : Gemini responses arrive (order depends on complexity)
T+2-4s  : Each user receives their personalized response
```

**Key points:**
- ✅ Each user's request is processed independently
- ✅ No waiting in queue - all process in parallel
- ✅ Responses are sent back to the correct user
- ✅ No cross-talk between conversations

### Scenario 2: Same User Sends Multiple Messages Rapidly

**What happens:**
1. User A sends "What is diabetes?"
2. User A immediately sends "Actually, tell me about cancer"
3. User A sends "Never mind, explain heart disease"

**Bot behavior:**
```python
# In logic_handler.py
if "awaiting_response" in session:
    return  # Silently ignore new messages while processing
```

**Timeline:**
```
T+0ms   : "What is diabetes?" - starts processing
T+100ms : "Actually, tell me about cancer" - IGNORED
T+200ms : "Never mind, explain heart disease" - IGNORED
T+3s    : Gemini response about diabetes sent to user
T+3.1s  : Session unlocked, ready for new messages
```

**Key points:**
- ⚠️ Only the first message is processed
- ⚠️ Subsequent messages are silently dropped
- ℹ️ No error message sent to user
- ✅ Prevents response confusion

## 🔄 Processing States

### 1. Idle State
- Session exists but no active processing
- Ready to accept new messages
- Can handle text, audio, or commands

### 2. Processing State (`awaiting_response = True`)
- Currently waiting for Gemini API response
- New messages are ignored
- Session is "locked" for this user

### 3. Audio Processing State
- Converting speech to text (STT)
- Then moves to Processing State
- Additional complexity for voicemail handling

## 📝 Detailed Flow Examples

### Example 1: Text Message Flow
```python
1. User sends text message
2. get_user_session(user_id) retrieves/creates session
3. Check if session["awaiting_response"] == True
   - If True: return (ignore message)
   - If False: continue
4. Set session["awaiting_response"] = True
5. Send to Gemini API
6. Wait for response (1-5 seconds typically)
7. Generate TTS audio if needed
8. Send response to user
9. Set session["awaiting_response"] = False
```

### Example 2: Interrupted Audio Message
```python
1. User sends voice message
2. Start STT processing
3. User sends text "cancel" (during STT)
4. Text message is processed first (STT still running)
5. STT completes but finds session busy
6. STT result is discarded
```

## 🎯 Rate Limiting

### Global Rate Limit
```python
# Token bucket algorithm
if not _global_rate_limiter.check_and_consume():
    return "System busy, try again"
```

- **Tokens**: 100 total
- **Refill**: 10 tokens per second
- **Purpose**: Prevent API overload

### Per-User Rate Limit
```python
# Each user has their own bucket
if not await check_user_rate_limit(user_id):
    return "Slow down please"
```

- **Tokens**: 20 per user
- **Refill**: 1 token per second
- **Purpose**: Prevent single user abuse

## 🚨 Edge Cases & Solutions

### Edge Case 1: Gemini API Timeout
**Scenario**: Gemini takes >30 seconds to respond

**What happens**:
1. Request times out
2. Session remains locked
3. User can't send new messages

**Solution**:
```python
# Timeout handling in logic_handler
try:
    response = await gemini_api_call(timeout=30)
except TimeoutError:
    session["awaiting_response"] = False
    return "Request timed out, please try again"
```

### Edge Case 2: Concurrent Voice Messages
**Scenario**: User sends multiple voice messages rapidly

**What happens**:
1. First voice message starts STT
2. Second voice message queued
3. Both might process simultaneously
4. Results might arrive out of order

**Current behavior**: First STT result that completes gets processed

### Edge Case 3: Session Cleanup During Processing
**Scenario**: Session expires while Gemini is processing

**What happens**:
1. Cleanup job runs every 6 hours
2. Finds session older than 24 hours
3. Session deleted mid-processing

**Protection**:
```python
# Sessions aren't cleaned if currently active
if session.get("awaiting_response"):
    continue  # Skip cleanup for active sessions
```

## 📊 Performance Characteristics

### Response Times
- **Text input**: 1-3 seconds (Gemini only)
- **Voice input**: 2-5 seconds (STT + Gemini)
- **With TTS**: +1-2 seconds

### Concurrent Capacity
- **FastAPI Workers**: 1 (configured in Dockerfile)
- **Thread Pool**: Default (usually 40 threads)
- **Practical Limit**: ~20-30 concurrent users
- **Bottleneck**: Gemini API rate limits

### Memory Usage
- **Per Session**: ~1-5 KB (text history)
- **Per Audio File**: ~100-500 KB (cached in memory)
- **Total Memory**: Limited by 1GB storage cap

## 🔧 Configuration Options

### Enable Message Queueing (Not Implemented)
```python
# Potential enhancement
session["message_queue"] = []
if session["awaiting_response"]:
    session["message_queue"].append(message)
```

### Enable Response Interruption (Not Implemented)
```python
# Potential enhancement
if new_message == "stop":
    session["cancel_current"] = True
```

### Adjust Timeouts
```python
# In .env
GEMINI_TIMEOUT=30
STT_TIMEOUT=10
TTS_TIMEOUT=15
```

## 🎯 Best Practices for Users

1. **Wait for responses** before sending new messages
2. **Use text for urgent** interruptions (processed faster than voice)
3. **Avoid rapid-fire messages** - they will be ignored
4. **One question at a time** for best results

## 🔍 Debugging Concurrency Issues

### Check Session State
```python
# Add to logic_handler for debugging
print(f"Session {user_id}: {session.get('awaiting_response')}")
```

### Monitor Active Sessions
```python
# Add endpoint to check active sessions
@app.get("/debug/sessions")
async def get_active_sessions():
    active = sum(1 for s in sessions.values() 
                 if s.get("awaiting_response"))
    return {"active": active, "total": len(sessions)}
```

### Log Timing
```python
# Add timing logs
start_time = time.time()
# ... process ...
print(f"Processing took {time.time() - start_time}s")
```

## 📈 Scalability Considerations

### Current Limitations
1. Single worker process (no horizontal scaling)
2. In-memory sessions (lost on restart)
3. Gemini API rate limits
4. No message queue

### Potential Improvements
1. Redis for session storage
2. Celery for async task queue
3. Multiple worker processes
4. WebSocket for real-time updates
5. Message queue for handling bursts

## 🎬 Summary

MedEdBot handles concurrency through:
- **Session isolation**: Each user has their own conversation state
- **Thread safety**: Locks prevent race conditions
- **Message dropping**: Ignores messages during processing
- **Rate limiting**: Prevents system overload
- **Timeout protection**: Ensures sessions don't stay locked

This design prioritizes **simplicity and reliability** over complex queueing mechanisms, making it suitable for moderate concurrent usage while preventing confusing bot behaviors.