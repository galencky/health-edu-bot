# 🏗️ MedEdBot Architecture Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Request Flow](#request-flow)
5. [Data Flow](#data-flow)
6. [Key Design Patterns](#key-design-patterns)
7. [Module Interactions](#module-interactions)
8. [Debugging Guide](#debugging-guide)

## 🎯 Project Overview

MedEdBot is a multilingual medical education and translation chatbot designed for healthcare professionals in Taiwan. It integrates with LINE messaging platform and uses Google Gemini AI to:
- Generate patient education materials
- Translate medical conversations in real-time
- Convert speech to text and text to speech
- Send educational content via email

## 🏛️ System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   LINE Users    │────▶│  LINE Platform   │────▶│   LINE Webhook  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      Request Router                          │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────┬───────────┴───────────┬──────────────┐          │
│  │   Handlers   │      Services         │   Utilities   │          │
│  │              │                       │               │          │
│  │ - LINE      │  - Gemini AI          │ - Database    │          │
│  │ - Logic     │  - TTS/STT            │ - Logging     │          │
│  │ - MedChat   │  - Email              │ - Storage     │          │
│  │ - Session   │  - Google Drive       │ - Validators  │          │
│  └──────────────┴───────────────────────┴──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ PostgreSQL   │      │ Google Drive │      │ Local/Memory │
│   Database   │      │   Storage    │      │   Storage    │
└──────────────┘      └──────────────┘      └──────────────┘
```

## 🔧 Core Components

### 1. Entry Points

#### `main.py`
- **Purpose**: FastAPI application entry point
- **Key Functions**:
  - Sets up FastAPI app with middleware
  - Configures CORS for web access
  - Mounts static file serving for audio
  - Includes route modules
  - Initializes database on startup

#### `routes/webhook.py`
- **Purpose**: LINE webhook endpoint
- **Flow**:
  1. Receives POST requests from LINE
  2. Validates webhook signature
  3. Parses events (text/audio messages)
  4. Delegates to appropriate handlers
  5. Returns HTTP 200 to acknowledge

### 2. Message Handlers

#### `handlers/line_handler.py`
- **Purpose**: Process LINE messages (text/audio)
- **Key Functions**:
  - `handle_line_message()`: Process text messages
    - Checks for STT translation flow
    - Handles TTS audio queuing
    - Routes to logic handler
    - Manages LINE API responses
  - `handle_audio_message()`: Process voice messages
    - Downloads audio from LINE
    - Saves to disk/memory
    - Calls STT service
    - Manages translation flow

#### `handlers/logic_handler.py`
- **Purpose**: Central routing logic for commands
- **Key Functions**:
  - `handle_user_message()`: Main dispatcher
    - Routes between Education and MedChat modes
    - Handles command parsing
    - Manages session state transitions
  - Mode-specific flows:
    - Education: Generate → Modify → Translate → Email
    - MedChat: Set language → Real-time translation

#### `handlers/medchat_handler.py`
- **Purpose**: Medical chat translation mode
- **Flow**:
  1. Check/set target language
  2. Plainify Chinese input
  3. Translate to target language
  4. Return bilingual response
  5. Enable TTS options

#### `handlers/session_manager.py`
- **Purpose**: In-memory session state management
- **Key Features**:
  - Thread-safe with RLock
  - Stores user preferences
  - Tracks conversation state
  - No persistence (memory only)

### 3. AI Services

#### `services/gemini_service.py`
- **Purpose**: Google Gemini AI integration
- **Key Functions**:
  - `_call_genai()`: Core API caller with timeout/retry
  - `call_zh()`: Generate Chinese content
  - `call_translate()`: Translate content
  - `plainify()`: Simplify medical Chinese
  - `confirm_translate()`: Translate with confirmation
  - `get_references()`: Extract search results
- **Features**:
  - Rate limiting (60 requests/minute)
  - Thread-local storage for responses
  - Google search integration
  - Timeout protection (50s)

#### `services/stt_service.py`
- **Purpose**: Speech-to-text using Gemini
- **Flow**:
  1. Upload audio to Gemini Files API
  2. Call generate_content with transcription prompt
  3. Return formatted transcript with language detection
  4. Clean up uploaded file

#### `services/tts_service.py`
- **Purpose**: Text-to-speech using Gemini
- **Flow**:
  1. Split text into chunks (≤200 chars)
  2. Generate audio for each chunk
  3. Merge audio files if multiple chunks
  4. Save to disk or memory storage
  5. Log to database and Google Drive

### 4. Storage Systems

#### `utils/storage_config.py`
- **Purpose**: Determine storage backend
- **Logic**:
  ```
  if PORT != "10001" (cloud deployment) → Memory Storage
  else (local/Synology) → Disk Storage
  ```

#### `utils/memory_storage.py`
- **Purpose**: In-memory file storage for cloud
- **Features**:
  - LRU eviction (100 files max)
  - TTL support (24 hours default)
  - Thread-safe operations
  - Returns (data, content_type) tuples

#### `utils/paths.py`
- **Purpose**: Centralized path management
- **Provides**:
  - Base directories
  - Safe path creation
  - Cross-platform compatibility

### 5. External Integrations

#### `utils/google_drive_service.py`
- **Purpose**: Google Drive file uploads
- **Functions**:
  - `upload_gemini_log()`: Upload chat logs
  - `upload_stt_translation_log()`: Upload STT translations
  - Service account authentication
  - Retry logic for reliability

#### `utils/email_service.py`
- **Purpose**: Send education materials via email
- **Features**:
  - SMTP with Gmail
  - HTML email formatting
  - Reference links inclusion
  - Input validation

### 6. Database Layer

#### `utils/database.py`
- **Purpose**: PostgreSQL operations
- **Features**:
  - Async SQLAlchemy
  - Connection pooling
  - Automatic retries
  - Three tables: chat_logs, tts_logs, voicemail_logs
- **Key Functions**:
  - `log_chat_to_db()`: Log conversations
  - `log_tts_to_db()`: Log TTS generation
  - Sync/async dual support

#### `utils/logging.py`
- **Purpose**: Coordinate logging operations
- **Features**:
  - Async wrappers for database
  - Google Drive uploads
  - Fire-and-forget pattern
  - Thread pool execution

### 7. Security & Validation

#### `utils/validators.py`
- **Purpose**: Input validation and sanitization
- **Validates**:
  - User IDs (LINE format)
  - Email addresses
  - File paths (prevent traversal)
  - Text content (length/format)
  - Action types

#### `utils/rate_limiter.py`
- **Purpose**: API rate limiting
- **Implementation**:
  - Token bucket algorithm
  - 60 requests/minute for Gemini
  - Per-user or global limits
  - Thread-safe

## 🔄 Request Flow

### Text Message Flow
```
LINE User → LINE Platform → Webhook → line_handler
    ↓
line_handler checks session state
    ↓
If STT translation pending → Process translation
Else → logic_handler
    ↓
logic_handler routes by mode:
    - Education → Generate/Modify/Translate/Email
    - MedChat → Translate conversation
    ↓
Gemini API calls
    ↓
Response formatting → LINE API → User
```

### Audio Message Flow
```
LINE User (audio) → LINE Platform → Webhook → line_handler
    ↓
Download audio → Save locally
    ↓
STT transcription (Gemini)
    ↓
Store in session → Request translation language
    ↓
User provides language → Translation (Gemini)
    ↓
Response with TTS option → User
```

## 📊 Data Flow

### Session Data
```python
session = {
    "started": True,
    "mode": "edu" | "chat" | None,
    
    # Education mode
    "zh_output": "Chinese content",
    "translated_output": "Translated content",
    "references": [{title, url}, ...],
    
    # MedChat mode
    "chat_target_lang": "English",
    
    # STT/TTS
    "stt_transcription": "Original text",
    "stt_last_translation": "Translated text",
    "tts_audio_url": "https://...",
    
    # State flags
    "awaiting_stt_translation": False,
    "awaiting_email": False,
    ...
}
```

### Database Schema
```sql
chat_logs:
- id, timestamp, user_id
- message, reply
- action_type: "sync reply" | "Gemini reply" | "medchat" | "translate"
- gemini_call: boolean
- gemini_output_url: Drive link

tts_logs:
- id, timestamp, user_id
- text, audio_filename, audio_url
- drive_link, status

voicemail_logs: (deprecated, no longer used)
```

## 🎨 Key Design Patterns

### 1. Async/Sync Dual Support
```python
# Async function with sync fallback
async def log_chat_to_db(...):
    if not ASYNC_AVAILABLE:
        return _log_chat_to_db_sync(...)
    # Async implementation
```

### 2. Fire-and-Forget Logging
```python
def log_chat_sync(...):
    def _worker():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_async_log_chat(...))
    threading.Thread(target=_worker, daemon=True).start()
```

### 3. Retry with Exponential Backoff
```python
@exponential_backoff(max_retries=3, initial_delay=1.0)
def risky_operation():
    # May fail transiently
```

### 4. Thread-Local Storage
```python
_thread_local = threading.local()
# Prevents race conditions in concurrent requests
```

## 🔍 Module Interactions

### Command Processing
```
User Input → logic_handler.handle_user_message()
    ↓
Parse commands (new, edu, chat, translate, etc.)
    ↓
Update session state
    ↓
Call appropriate service:
    - gemini_service for AI
    - email_service for sending
    - tts_service for audio
    ↓
Format response → Return to handler
```

### Storage Decision
```
storage_config.get_storage_backend()
    ↓
Check PORT environment variable
    ↓
PORT != "10001" → Memory (cloud)
PORT == "10001" → Disk (local/Synology)
```

### Logging Pipeline
```
Action occurs → log_chat() called
    ↓
If gemini_call="yes":
    → upload_gemini_log() to Drive
    ↓
log_chat_to_db() → PostgreSQL
    ↓
Both operations run async/threaded
```

## 🐛 Debugging Guide

### Common Issues & Solutions

#### 1. "Audio file not found"
- **Check**: Storage backend (memory vs disk)
- **Debug**: 
  ```python
  print(f"Storage: {TTS_USE_MEMORY}")
  print(f"Files: {memory_storage._cache.keys()}")
  ```

#### 2. Session state issues
- **Check**: Session flags and mode
- **Debug**: Add to handlers:
  ```python
  print(f"Session: {session}")
  ```

#### 3. Gemini timeouts
- **Check**: API_TIMEOUT_SECONDS (50s)
- **Debug**: Enable retry logging
- **Fix**: Reduce prompt complexity

#### 4. Database logging failures
- **Check**: CONNECTION_STRING format
- **Debug**: Test connection:
  ```python
  engine = get_async_db_engine()
  ```

#### 5. Permission errors (Synology)
- **Check**: UID/GID = 1000
- **Fix**: 
  ```bash
  chown -R 1000:1000 /path/to/data
  chmod 775 /path/to/data
  ```

### Debugging Tools

#### Enable Debug Logging
```python
# In .env
LOG_LEVEL=debug

# In code
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Trace Request Flow
```python
# Add to each handler
print(f"[{self.__class__.__name__}] Processing: {user_input}")
```

#### Monitor API Calls
```python
# In gemini_service._call_genai()
print(f"Gemini request: {user_text[:50]}...")
print(f"Gemini response: {response[:50]}...")
```

## 🔗 Key Integration Points

### LINE → Bot
- Webhook validates signature
- Parses events based on type
- Extracts user_id, message content
- Handles reply tokens (1-time use)

### Bot → Gemini
- Rate limited (60/min)
- Timeout protected (50s)
- Retry on failure
- Thread-local response storage

### Bot → Database
- Async operations
- Connection pooling
- Automatic reconnection
- Validation before insert

### Bot → Storage
- Automatic backend selection
- Memory: LRU cache with TTL
- Disk: Direct file operations
- Thread-safe access

This architecture allows for:
- Scalable cloud deployment (memory storage)
- Reliable local deployment (disk storage)
- Comprehensive logging and debugging
- Secure input handling
- Graceful error recovery