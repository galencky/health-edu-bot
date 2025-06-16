# MedEdBot Technical Details

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Request Processing Flow](#request-processing-flow)
4. [Session Management](#session-management)
5. [Storage Strategy](#storage-strategy)
6. [AI Integration](#ai-integration)
7. [Database Schema](#database-schema)
8. [Security Implementation](#security-implementation)
9. [Performance Optimizations](#performance-optimizations)
10. [Error Handling](#error-handling)

## Architecture Overview

MedEdBot follows a modular, event-driven architecture optimized for cloud deployment:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   LINE Users    │────▶│  LINE Platform   │────▶│   Webhook API   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                        ┌──────────────────────────────────┴──────────┐
                        │            FastAPI Application              │
                        │                                             │
                        │  ┌───────────────────────────────────────┐ │
                        │  │          Request Router               │ │
                        │  │    - Signature Verification           │ │
                        │  │    - Request Validation               │ │
                        │  │    - Route Distribution               │ │
                        │  └─────────────┬─────────────────────────┘ │
                        │                │                            │
                        │  ┌─────────────┴─────────────┐             │
                        │  │      Handler Layer        │             │
                        │  │                           │             │
                        │  │  ├── LINE Handler         │             │
                        │  │  ├── Logic Handler        │             │
                        │  │  ├── MedChat Handler      │             │
                        │  │  └── Session Handler      │             │
                        │  └─────────────┬─────────────┘             │
                        │                │                            │
                        │  ┌─────────────┴─────────────┐             │
                        │  │      Service Layer        │             │
                        │  │                           │             │
                        │  │  ├── Gemini AI Service    │             │
                        │  │  ├── TTS/STT Service      │             │
                        │  │  ├── Email Service        │             │
                        │  │  └── Google Drive Service │             │
                        │  └─────────────┬─────────────┘             │
                        │                │                            │
                        │  ┌─────────────┴─────────────┐             │
                        │  │       Utility Layer       │             │
                        │  │                           │             │
                        │  │  ├── Database Operations  │             │
                        │  │  ├── Storage Manager      │             │
                        │  │  ├── Input Validators     │             │
                        │  │  └── Logging System       │             │
                        │  └───────────────────────────┘             │
                        └─────────────────────────────────────────────┘
```

## Core Components

### 1. Handler Layer

**LINE Handler** (`handlers/line_handler.py`)
- Processes incoming LINE webhook events
- Validates LINE signatures using HMAC-SHA256
- Routes messages to appropriate handlers based on type
- Manages reply token lifecycle

**Logic Handler** (`handlers/logic_handler.py`)
- Implements business logic for education mode
- Handles menu navigation and content delivery
- Manages email sending functionality
- Processes user commands and interactions

**MedChat Handler** (`handlers/medchat_handler.py`)
- Manages medical Q&A conversations
- Integrates with Gemini AI for responses
- Implements context-aware conversations
- Handles TTS generation for responses

**Session Handler** (`handlers/session_handler.py`)
- Thread-safe session management
- Session persistence and cleanup
- User state tracking
- Concurrent request handling

### 2. Service Layer

**Gemini Service** (`services/gemini_service.py`)
- Async integration with Google Gemini API
- Content generation with medical grounding
- Retry logic with exponential backoff
- Token usage optimization

**TTS/STT Service** (`services/tts_service.py`, `services/stt_service.py`)
- Text-to-speech conversion using Gemini
- Speech-to-text transcription
- Multi-language support (zh-TW, en-US, ja-JP)
- Audio format handling and conversion

**Email Service** (`services/email_service.py`)
- SMTP integration with Gmail
- HTML email formatting
- Attachment support
- Email validation and sanitization

### 3. Utility Layer

**Database Operations** (`utils/database.py`)
- SQLAlchemy ORM integration
- Connection pooling
- Transaction management
- Query optimization

**Storage Manager** (`utils/storage_manager.py`)
- Adaptive storage strategy
- Memory storage for ephemeral environments
- Disk storage for persistent environments
- Automatic cleanup of temporary files

## Request Processing Flow

1. **Webhook Reception**
   ```python
   POST / → line_handler.handle_line_request()
   ```

2. **Signature Verification**
   ```python
   signature = hmac.new(
       channel_secret.encode('utf-8'),
       body.encode('utf-8'), 
       hashlib.sha256
   ).digest()
   ```

3. **Event Processing**
   ```python
   if event.type == "message":
       if event.message.type == "text":
           → process_text_message()
       elif event.message.type == "audio":
           → process_audio_message()
   ```

4. **Session Management**
   ```python
   session = get_user_session(user_id)
   with session.lock:
       # Process request
   ```

5. **Response Generation**
   ```python
   response = await gemini_service.generate_content(prompt)
   ```

6. **Reply Delivery**
   ```python
   line_bot_api.reply_message(reply_token, messages)
   ```

## Session Management

### Thread-Safe Implementation
```python
class UserSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.lock = threading.RLock()
        self.history = []
        self.state = {}
        self.last_activity = datetime.now()
```

### Session Lifecycle
- **Creation**: On first user interaction
- **Updates**: Thread-safe with reentrant locks
- **Cleanup**: After 30 minutes of inactivity
- **Persistence**: In-memory with optional disk backup

## Storage Strategy

### Adaptive Storage Detection
```python
def _detect_storage_type() -> StorageType:
    if os.environ.get('RENDER', False):
        return StorageType.MEMORY
    
    test_file = '/tmp/storage_test'
    if _can_write_file(test_file):
        return StorageType.DISK
    
    return StorageType.MEMORY
```

### Storage Implementations

**Memory Storage**
- Used in ephemeral environments (Render, Heroku)
- Base64 encoding for data persistence
- Size limits to prevent memory exhaustion
- Automatic garbage collection

**Disk Storage**
- Used in persistent environments (Synology, VPS)
- File-based with proper permissions
- Automatic directory creation
- Cleanup of old files

## AI Integration

### Gemini Configuration
```python
generation_config = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 2048,
}

safety_settings = [
    {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
]
```

### Medical Grounding
- Uses Gemini's grounding feature for medical accuracy
- Implements search integration for up-to-date information
- Validates medical content against safety guidelines

## Database Schema

### Tables

**conversation_logs**
```sql
CREATE TABLE conversation_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    message TEXT,
    reply TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(50),
    processing_time FLOAT,
    error_message TEXT
);
```

**Indexes**
```sql
CREATE INDEX idx_user_id ON conversation_logs(user_id);
CREATE INDEX idx_timestamp ON conversation_logs(timestamp);
```

## Security Implementation

### Input Validation
```python
def validate_user_input(text: str) -> tuple[bool, str]:
    # Length check
    if len(text) > 1000:
        return False, "Message too long"
    
    # Pattern validation
    if contains_malicious_patterns(text):
        return False, "Invalid input"
    
    # Encoding validation
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        return False, "Invalid characters"
    
    return True, text
```

### Rate Limiting
```python
rate_limiter = RateLimiter(
    max_requests=30,
    window_seconds=60,
    burst_size=5
)
```

### Signature Verification
```python
def verify_signature(body: str, signature: str, secret: str) -> bool:
    hash = hmac.new(
        secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return hmac.compare_digest(
        hash,
        base64.b64decode(signature)
    )
```

## Performance Optimizations

### 1. Async I/O
- All external API calls use async/await
- Non-blocking database operations
- Concurrent request processing

### 2. Connection Pooling
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 3. Caching Strategy
- In-memory session caching
- Response caching for common queries
- File caching for frequently accessed content

### 4. Resource Management
- Automatic cleanup of temporary files
- Memory usage monitoring
- Connection limit enforcement

## Error Handling

### Error Categories

1. **User Errors**: Invalid input, rate limits
2. **System Errors**: API failures, database issues
3. **Integration Errors**: LINE API, Gemini API
4. **Resource Errors**: Storage, memory limits

### Error Response Flow
```python
try:
    # Process request
except UserError as e:
    # Return user-friendly message
    log_error(e, level="warning")
except SystemError as e:
    # Return generic error message
    log_error(e, level="error")
    notify_admin(e)
except Exception as e:
    # Return fallback message
    log_error(e, level="critical")
    return "System temporarily unavailable"
```

### Logging Strategy
- Structured logging with context
- Error aggregation and alerting
- Performance metrics tracking
- User activity monitoring