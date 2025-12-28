# Mededbot Architecture Analysis

## Project Overview
Mededbot is a **multilingual medical education and translation chatbot** built with FastAPI and deployed as a LINE Bot. It provides two core modes:
1. **Education Mode**: Generate health education materials in Chinese and translate them to multiple languages
2. **Medical Translation Mode (MedChat)**: Real-time medical translation with voice support

---

## File Organization & Responsibilities

### 1. Entry Point & Application Core

#### [main.py](main.py)
**Purpose**: FastAPI application entry point and lifecycle management

**Key Responsibilities**:
- Initializes FastAPI application with lifespan management
- Mounts static file serving for audio files (`/static`)
- Includes webhook router for LINE Bot integration
- Provides health check endpoints (`/health`, `/ping`)
- Implements periodic cleanup tasks (sessions, audio files)
- Handles audio file serving from memory storage (`/audio/{filename}`)
- Test endpoint for chat functionality (`/chat`)

**Dependencies**:
- `routes.webhook` - webhook handling
- `handlers.session_manager` - session management
- `handlers.logic_handler` - message processing
- `utils.storage_config` - storage configuration
- `utils.memory_storage` - in-memory file storage

**Flow**:
```
Startup → Database connection test → Background cleanup task → Ready
Shutdown → Cancel cleanup → Final cleanup → Exit
```

---

### 2. Request Routing Layer

#### [routes/webhook.py](routes/webhook.py)
**Purpose**: Handle LINE Bot webhook events with timeout protection

**Key Responsibilities**:
- Receives webhook POST requests from LINE platform
- Validates LINE signature for security
- Routes events to appropriate handlers
- Implements 48-second timeout protection
- Handles text messages, audio messages, stickers, and images
- Always returns "OK" to prevent LINE webhook retries (even on errors)

**Event Flow**:
```
LINE webhook → Signature validation → Event type detection → Handler dispatch → Response
```

**Handler Mapping**:
- `TextMessage` → `handle_line_message()`
- `AudioMessage` → `handle_audio_message()`
- `StickerMessage/ImageMessage` → `fallback_handler()`

---

### 3. Message Handling Layer

#### [handlers/line_handler.py](handlers/line_handler.py)
**Purpose**: Process LINE-specific message formats and create response bubbles

**Key Responsibilities**:
- Handle text messages: extract user input, process through logic handler
- Handle audio messages: save, transcribe, process as text
- Create message bubbles for LINE responses (text, audio, flex messages)
- Manage LINE's message limits (5 bubbles, 300k characters total)
- Handle Taigi credit attribution for Taiwanese TTS
- Implement message splitting and truncation
- Audio rejection based on session state

**Message Creation Flow**:
```
Session state → Check for audio/credit → Add content bubbles → Add references → Add main reply → Validate limits
```

**Audio Message Flow**:
```
Audio received → Check mode (chat only) → Save file → Transcribe → Delete file → Process as text → Create response
```

#### [handlers/logic_handler.py](handlers/logic_handler.py)
**Purpose**: Core business logic dispatcher - routes messages to appropriate handlers

**Key Responsibilities**:
- Main message routing based on session state
- Handle global commands (`new`, `speak`)
- Route to education mode or chat mode handlers
- Process education mode: content generation, modification, translation, email
- Manage awaiting states (waiting for user input)
- Language selection and validation

**Message Flow**:
```
User message → Session check → Command detection → Mode routing → Handler execution → Response generation
```

**State Machine**:
- Not started → Show welcome
- Mode selection → Education/Chat
- Education mode → Generate/Modify/Translate/Email
- Chat mode → Language selection → Translation

#### [handlers/medchat_handler.py](handlers/medchat_handler.py)
**Purpose**: Handle medical translation conversations (chat mode)

**Key Responsibilities**:
- Language selection workflow
- Text simplification (medical → plain language)
- Translation using Gemini or Taigi service
- Continue translation command
- Store results in session for TTS generation

**Translation Flow**:
```
Raw text → Plainify (simplify) → Translate to target language → Confirmation format → Log
```

**Special Handling**:
- Taiwanese (Taigi): Uses dedicated Taigi service instead of Gemini
- Other languages: Uses Gemini API

#### [handlers/mail_handler.py](handlers/mail_handler.py)
**Purpose**: Handle email sending with content upload to R2

**Key Responsibilities**:
- Compose email body (original + translation + references)
- Upload email content to R2 storage for logging
- Send email via Gmail SMTP
- Return success status and R2 URL

**Email Flow**:
```
Session content → Compose body → Upload to R2 → Send email → Return status
```

---

### 4. Session Management

#### [handlers/session_manager.py](handlers/session_manager.py)
**Purpose**: Thread-safe in-memory session storage

**Key Responsibilities**:
- Store user sessions in memory (dictionary-based)
- Thread-safe access with locks (per-user and global locks)
- Session expiry (24 hours)
- Periodic cleanup of expired sessions

**Thread Safety**:
- Global lock for session creation/deletion
- Per-user locks for session access
- RLock (reentrant) for nested locking

**Storage**:
```python
_sessions: Dict[str, Dict]  # user_id → session data
_session_locks: Dict[str, RLock]  # user_id → lock
_session_last_access: Dict[str, datetime]  # user_id → timestamp
```

---

### 5. AI Services Layer

#### [services/gemini_service.py](services/gemini_service.py)
**Purpose**: Interface to Google Gemini AI with grounding and references

**Key Responsibilities**:
- Generate Chinese health education content
- Translate content to any language
- Simplify medical language (plainify)
- Extract references from grounding metadata
- Convert references to LINE Flex Message format
- Circuit breaker and rate limiting protection
- Retry logic for API failures

**API Functions**:
- `call_zh()` - Generate Chinese content with Google Search grounding
- `call_translate()` - Translate to target language
- `plainify()` - Simplify text to plain language
- `confirm_translate()` - Translate simplified text
- `get_references()` - Extract references from last response
- `references_to_flex()` - Convert to LINE format

**Configuration**:
- Model: `gemini-2.5-flash`
- Timeout: 45 seconds
- Retries: 2 attempts with 3s delay
- Tools: Google Search for grounding

#### [services/tts_service.py](services/tts_service.py)
**Purpose**: Text-to-speech using Gemini TTS API

**Key Responsibilities**:
- Synthesize speech from text
- Save audio as WAV files (disk or memory)
- Upload to R2 storage asynchronously
- Generate public URLs for audio playback
- Rate limiting (20 requests/minute)

**Storage Modes**:
- **Memory**: Save to `memory_storage`, serve via `/audio/{filename}`
- **Disk**: Save to `tts_audio/`, serve via `/static/{filename}`

**Audio Generation Flow**:
```
Text → Validate → Call Gemini TTS API → Get PCM data → Convert to WAV → Save → Upload to R2 → Return URL
```

**Model**: `gemini-2.5-flash-preview-tts`

#### [services/taigi_service.py](services/taigi_service.py)
**Purpose**: Taiwanese (Taigi) translation and TTS using NYCU service

**Key Responsibilities**:
- Translate Chinese to Taigi (TLPA romanization)
- Generate Taigi speech from Chinese text
- Rate limiting (30 requests/minute)
- Error handling for external service

**External API**:
- Base URL: `http://tts001.ivoice.tw:8804/`
- Translation: `/html_taigi_zh_tw_py`
- TTS: `/synthesize_TLPA`

**Flow**:
```
Chinese text → TLPA translation → TTS synthesis → WAV audio → Save/Upload
```

**Configuration**:
- Gender: Female (女聲)
- Accent: Strong (高雄腔)

#### [services/stt_service.py](services/stt_service.py)
**Purpose**: Speech-to-text transcription using Gemini

**Key Responsibilities**:
- Upload audio file to Gemini Files API
- Transcribe audio to text
- Clean up transcription (remove fillers, fix errors)

**Audio Support**:
- Formats: M4A, AAC, MP3, WAV, OGG, FLAC, AIFF
- MIME type detection and fallback
- Inline data approach for Docker compatibility

**Model**: `gemini-2.5-flash`

#### [services/prompt_config.py](services/prompt_config.py)
**Purpose**: System prompts for Gemini AI (not shown but imported)

**Prompts**:
- `zh_prompt` - Health education content generation
- `translate_prompt_template` - Translation instructions
- `plainify_prompt` - Medical language simplification
- `confirm_translate_prompt` - Translation confirmation
- `modify_prompt` - Content modification

---

### 6. Database & Logging

#### [utils/database.py](utils/database.py)
**Purpose**: PostgreSQL database interface with async/sync support

**Key Responsibilities**:
- Database models: `ChatLog`, `TTSLog`, `VoicemailLog`
- Async and sync database connections (PostgreSQL)
- Session management with context managers
- Input validation and sanitization
- Async/sync fallback for compatibility

**Models**:
- **ChatLog**: User messages, replies, action types, Gemini calls
- **TTSLog**: TTS generation, audio files, R2 links
- **VoicemailLog**: Audio transcription, translation

**Connection**:
- Async: `postgresql+asyncpg://`
- Sync: `postgresql://`
- Pool: 5 connections, 10 max overflow
- SSL required

#### [utils/logging.py](utils/logging.py)
**Purpose**: Async logging with R2 upload and database storage

**Key Responsibilities**:
- Log chat interactions to database
- Upload Gemini outputs to R2 storage
- Log TTS generation with audio upload
- Background task execution with thread pool
- Smart async/sync context detection

**Functions**:
- `log_chat()` - Smart wrapper (async or sync)
- `log_tts_async()` - Fire-and-forget TTS logging
- `upload_voicemail()` - Upload voicemail with retry

**Thread Pool**:
- Max 5 workers to prevent resource exhaustion
- Bounded execution to avoid unlimited thread creation

---

### 7. Storage Services

#### [utils/r2_service.py](utils/r2_service.py)
**Purpose**: Cloudflare R2 object storage interface

**Key Responsibilities**:
- Upload files to R2 bucket
- Generate public URLs
- Handle text files (UTF-8 encoding)
- Handle audio files (WAV, MP3, etc.)
- Upload Gemini logs with metadata

**R2 Structure**:
```
mededbot/
├── text/{user_id}/{user_id}-{timestamp}.txt
├── tts_audio/{user_id}/{filename}.wav
├── voicemail/{user_id}/{filename}.m4a
└── audio/{user_id}/{filename}
```

**Public URL**: `https://galenchen.uk/{key}`

#### [utils/memory_storage.py](utils/memory_storage.py)
**Purpose**: In-memory file storage for audio files (not shown but used)

**Features**:
- Store audio files in RAM
- Avoid disk I/O for better performance
- Automatic cleanup of old files
- Content-type tracking

#### [utils/storage_config.py](utils/storage_config.py)
**Purpose**: Storage backend configuration (not shown but imported)

**Settings**:
- `TTS_USE_MEMORY`: Use memory storage vs disk
- `TTS_USE_R2`: Enable R2 uploads

---

### 8. Email Service

#### [utils/email_service.py](utils/email_service.py)
**Purpose**: Send emails via Gmail SMTP

**Key Responsibilities**:
- Send health education materials to users
- Input validation (email format)
- Add disclaimer to all emails
- SSL connection to Gmail

**Configuration**:
- SMTP: `smtp.gmail.com:465` (SSL)
- Credentials: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`

---

### 9. Utility Services

#### [utils/rate_limiter.py](utils/rate_limiter.py)
**Purpose**: Token bucket rate limiting for API protection

**Key Responsibilities**:
- Sliding window rate limiting
- Per-user or per-service limits
- Thread-safe with locks
- Automatic cleanup of old entries

**Global Limiters**:
- `gemini_limiter`: 30 requests/minute
- `tts_limiter`: 20 requests/minute

**Algorithm**: Token bucket with sliding window

#### [utils/circuit_breaker.py](utils/circuit_breaker.py)
**Purpose**: Circuit breaker pattern for external services

**Key Responsibilities**:
- Prevent cascading failures
- Three states: CLOSED, OPEN, HALF_OPEN
- Automatic recovery attempts
- Failure threshold tracking

**Configuration**:
- `gemini_circuit_breaker`: 5 failures, 60s recovery

**States**:
- **CLOSED**: Normal operation
- **OPEN**: Block all calls after failures
- **HALF_OPEN**: Test if service recovered

#### [utils/validators.py](utils/validators.py)
**Purpose**: Input validation and sanitization (not shown but used)

**Functions**:
- `sanitize_user_id()` - Prevent path traversal
- `sanitize_filename()` - Safe filenames
- `sanitize_text()` - Clean user input
- `validate_email()` - Email format validation
- `create_safe_path()` - Secure file paths

#### [utils/retry_utils.py](utils/retry_utils.py)
**Purpose**: Exponential backoff retry logic (not shown but used)

**Features**:
- Configurable retry attempts
- Exponential delay with jitter
- Exception filtering
- Retry callbacks

#### [utils/command_sets.py](utils/command_sets.py)
**Purpose**: Command definitions and quick reply templates

**Commands**:
- `new_commands`: {"new", "開始"}
- `edu_commands`: {"ed", "education", "衛教"}
- `chat_commands`: {"chat", "聊天"}
- `modify_commands`: {"modify", "修改"}
- `translate_commands`: {"translate", "翻譯"}
- `mail_commands`: {"mail", "寄送"}
- `speak_commands`: {"speak", "朗讀"}

**Quick Reply Sets**:
- Mode selection (教育/翻譯)
- Common languages (10 languages)
- Common diseases (8 conditions)
- TTS options

#### [utils/language_utils.py](utils/language_utils.py)
**Purpose**: Language name normalization (not shown but used)

**Features**:
- Normalize language input (e.g., "英文" → "English")
- Support multiple language formats
- Taigi special handling

#### [utils/message_splitter.py](utils/message_splitter.py)
**Purpose**: Split long messages for LINE limits (not shown but used)

**Limits**:
- Max 5 bubbles per message
- Max 300k characters total
- Max 5k characters per bubble

#### [utils/quick_reply_templates.py](utils/quick_reply_templates.py)
**Purpose**: Quick reply button templates (not shown but used)

**Templates**:
- START: Welcome screen
- EDU_ACTIONS: Education mode actions
- COMMON languages
- CHAT_TTS: Chat mode with TTS

#### [utils/taigi_credit.py](utils/taigi_credit.py)
**Purpose**: Create attribution bubble for Taigi service (not shown but used)

**Content**: Credit to NYCU for Taiwanese TTS technology

---

### 10. Data Models

#### [models/session.py](models/session.py)
**Purpose**: Pydantic models for session management

**Models**:
- `SessionBase`: Common session fields
- `EducationSession`: Education mode fields
- `MedChatSession`: Chat mode fields
- `STTSession`: Speech-to-text fields
- `TTSSession`: Text-to-speech fields
- `UserSession`: Combined session model

**Features**:
- Pydantic v2 validation
- Legacy dict compatibility
- Type safety for gradual migration

#### [models/email_log.py](models/email_log.py)
**Purpose**: Structured email logging model

**Fields**:
- Timestamp, user ID, recipient
- Subject, topic, language
- Content, lengths, reference count

**Usage**: Create structured logs for R2 upload

---

## Data Flow Diagrams

### 1. Text Message Flow
```
LINE User → Webhook → line_handler → logic_handler → Session Manager
                                           ↓
                                    Mode Detection
                                    ↓            ↓
                           Education Mode    Chat Mode
                                ↓                ↓
                           call_zh()      plainify() + confirm_translate()
                           call_translate()       ↓
                                ↓            translate_to_taigi()
                           Gemini API      or Gemini API
                                ↓                ↓
                           get_references() Session Update
                                ↓                ↓
                           Session Update   Response Creation
                                ↓                ↓
                           Response Creation  LINE Bot API
                                ↓
                           LINE Bot API
                                ↓
                           log_chat() → Database + R2
```

### 2. Audio Message Flow (Chat Mode Only)
```
LINE Audio → Webhook → line_handler → save_audio_file()
                                           ↓
                                    transcribe_audio_file()
                                           ↓
                                    Gemini STT API
                                           ↓
                                    delete_audio_file()
                                           ↓
                                    medchat_handler (as text)
                                           ↓
                                    plainify() + translate
                                           ↓
                                    Response with transcription indicator
```

### 3. TTS Generation Flow
```
User: "朗讀" → logic_handler → synthesize() or synthesize_taigi()
                                      ↓              ↓
                              Gemini TTS API    NYCU Taigi API
                                      ↓              ↓
                              PCM → WAV         WAV bytes
                                      ↓              ↓
                              Save (memory/disk)  Save (memory/disk)
                                      ↓              ↓
                              Session: tts_audio_url
                                      ↓
                              line_handler creates AudioSendMessage
                                      ↓
                              LINE Bot API plays audio
                                      ↓
                              Background: log_tts_async() → R2 upload
```

### 4. Email Flow
```
User: email@example.com → logic_handler → mail_handler
                                              ↓
                                    Compose email body
                                    (original + translation + refs)
                                              ↓
                                    EmailLog.create()
                                              ↓
                                    Upload to R2 (text file)
                                              ↓
                                    send_email() via Gmail SMTP
                                              ↓
                                    Return success + R2 URL
                                              ↓
                                    Store R2 URL in session
                                              ↓
                                    log_chat() records R2 URL
```

---

## External Dependencies & APIs

### 1. Google Gemini API
- **Model**: `gemini-2.5-flash` (text), `gemini-2.5-flash-preview-tts` (audio)
- **Features**: Content generation, translation, STT, TTS, grounding
- **Rate Limit**: 30 requests/minute (app-level)
- **Circuit Breaker**: 5 failures → 60s recovery

### 2. NYCU Taigi Service
- **Endpoint**: `http://tts001.ivoice.tw:8804/`
- **Features**: Chinese → Taigi translation, Taigi TTS
- **Rate Limit**: 30 requests/minute
- **Timeout**: 30s (translation), 60s (TTS)

### 3. LINE Messaging API
- **Webhook**: Receives user messages
- **Send API**: Sends responses (text, audio, flex messages)
- **Limits**: 5 bubbles, 300k chars total

### 4. Cloudflare R2
- **Purpose**: File storage (logs, audio)
- **Access**: S3-compatible API
- **Public URL**: `https://galenchen.uk/`

### 5. PostgreSQL (Neon)
- **Database**: Session logs, chat logs, TTS logs
- **Connection**: Async (asyncpg) or sync
- **SSL**: Required

### 6. Gmail SMTP
- **Purpose**: Send health education emails
- **Port**: 465 (SSL)
- **Auth**: App password

---

## Key Design Patterns

### 1. Circuit Breaker Pattern
**Location**: `utils/circuit_breaker.py`, `services/gemini_service.py`

**Purpose**: Prevent cascading failures from external service issues

**Implementation**:
- Track failure count
- Open circuit after threshold
- Automatic recovery attempts

### 2. Rate Limiting Pattern
**Location**: `utils/rate_limiter.py`

**Purpose**: Protect against API abuse and quota exhaustion

**Implementation**:
- Token bucket algorithm
- Sliding window tracking
- Per-user and global limits

### 3. Retry with Exponential Backoff
**Location**: `utils/retry_utils.py`, `services/gemini_service.py`

**Purpose**: Handle transient failures gracefully

**Implementation**:
- Configurable retry attempts
- Exponential delay
- Jitter to avoid thundering herd

### 4. Session State Machine
**Location**: `handlers/logic_handler.py`, `handlers/session_manager.py`

**Purpose**: Manage complex conversation flows

**States**:
- Not started
- Mode selection
- Education mode (with sub-states)
- Chat mode (with sub-states)

### 5. Strategy Pattern (Storage)
**Location**: `utils/storage_config.py`, `utils/memory_storage.py`

**Purpose**: Switch between storage backends

**Strategies**:
- Memory storage
- Disk storage
- R2 cloud storage

### 6. Decorator Pattern (Rate Limiting)
**Location**: `utils/rate_limiter.py`

**Purpose**: Add rate limiting to functions declaratively

**Usage**:
```python
@rate_limit(gemini_limiter, key_func=lambda text, user_id: user_id)
def synthesize(text, user_id):
    ...
```

### 7. Factory Pattern (Email Logs)
**Location**: `models/email_log.py`

**Purpose**: Create structured email logs

**Usage**:
```python
email_log = EmailLog.create(user_id, to_email, subject, ...)
```

### 8. Proxy Pattern (Session Migration)
**Location**: `models/session.py`

**Purpose**: Support gradual migration from dict to Pydantic models

**Implementation**: `SessionProxy` provides dict interface backed by Pydantic model

---

## Thread Safety & Concurrency

### 1. Session Manager Locks
- **Global Lock**: For session creation/deletion
- **Per-User Locks**: For session access
- **Type**: `threading.RLock` (reentrant)

### 2. Rate Limiter Locks
- **Lock**: `threading.Lock` for timestamp deque access
- **Thread-safe**: All operations protected

### 3. Circuit Breaker Locks
- **Lock**: `threading.RLock` for state changes
- **Thread-safe**: State transitions protected

### 4. Async Context Detection
**Location**: `utils/logging.py`

**Pattern**: Detect if running in async context
```python
try:
    loop = asyncio.get_running_loop()
    # Use asyncio.create_task()
except RuntimeError:
    # Use threading or asyncio.run()
```

### 5. Thread Pool Executors
- **Logging**: 5 workers (`_logging_executor`)
- **R2 Upload**: 3 workers (`_r2_executor`)
- **Gemini**: 4 workers (`_executor`)

---

## Security Considerations

### 1. Input Validation
- User IDs: Sanitize to prevent path traversal
- Filenames: Sanitize to prevent directory escape
- Email addresses: Validate format and MX records
- Text content: Sanitize for length and characters

### 2. LINE Webhook Signature Validation
- Verify all webhook requests are from LINE
- Reject invalid signatures silently

### 3. Database Input Sanitization
- Validate all inputs before database insertion
- Use parameterized queries (SQLAlchemy ORM)

### 4. Error Message Sanitization
- Never expose internal paths or credentials
- Generic error messages to users

### 5. API Key Management
- Environment variables only
- Never committed to repository
- Fail fast if missing

---

## Performance Optimizations

### 1. Memory Storage for Audio
- Avoid disk I/O for temporary audio files
- Faster serving via `/audio/` endpoint
- Automatic cleanup

### 2. Background Upload Tasks
- Fire-and-forget R2 uploads
- Don't block user responses
- Thread pool limits resource usage

### 3. Connection Pooling
- Database: 5 base connections, 10 overflow
- Gemini: 4 worker threads
- R2: 3 worker threads

### 4. Message Splitting & Truncation
- Pre-calculate character counts
- Split long content to fit LINE limits
- Avoid API errors from oversized messages

### 5. Periodic Cleanup
- Hourly cleanup of expired sessions
- Remove old audio files
- Prevent memory leaks

---

## Error Handling Strategy

### 1. Graceful Degradation
- Continue operation even if logging fails
- Return user-friendly error messages
- Never expose stack traces to users

### 2. Always Return OK to LINE
- Prevent webhook retry storms
- Log errors internally
- User sees error message in chat

### 3. Retry Logic
- Gemini API: 2 retries with 3s delay
- R2 Upload: 3 retries with exponential backoff
- Circuit breaker for repeated failures

### 4. Fallback Paths
- Async → sync fallback for database
- Memory → disk fallback for storage
- Relative URLs if BASE_URL not configured

---

## Configuration Management

### Environment Variables
```
# Core
PORT=8080
BASE_URL=https://your-domain.com

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=xxx
LINE_CHANNEL_SECRET=xxx

# Gemini AI
GEMINI_API_KEY=xxx

# Database
DATABASE_URL=postgresql://user:pass@host/db

# Email
GMAIL_ADDRESS=xxx
GMAIL_APP_PASSWORD=xxx

# R2 Storage
R2_ENDPOINT_URL=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=mededbot

# Storage Config
TTS_USE_MEMORY=true/false
TTS_USE_R2=true/false
```

---

## Testing Recommendations

### Unit Tests
- `validators.py`: Input sanitization
- `rate_limiter.py`: Rate limiting logic
- `circuit_breaker.py`: State transitions
- `message_splitter.py`: Message splitting

### Integration Tests
- Gemini API calls with mocking
- Database operations (in-memory SQLite)
- Email sending (mock SMTP)
- R2 uploads (mock boto3)

### End-to-End Tests
- Complete conversation flows
- Mode switching
- Audio processing
- Email delivery

---

## Deployment Considerations

### 1. Environment
- FastAPI with Uvicorn
- Async/await for I/O operations
- Multi-threaded for background tasks

### 2. Scaling
- Stateless design (sessions in memory, but can migrate to Redis)
- Horizontal scaling possible if sessions externalized
- Database connection pooling

### 3. Monitoring
- Health check endpoints (`/health`, `/ping`)
- Database connectivity check on startup
- Logging to stdout/stderr

### 4. Resource Limits
- Thread pools bounded to prevent exhaustion
- Rate limiting to prevent API quota issues
- Memory storage cleanup to prevent OOM

---

## Future Improvements

### 1. Session Persistence
- Migrate from in-memory to Redis
- Enable horizontal scaling
- Persist across restarts

### 2. Observability
- Add structured logging (JSON)
- Integrate error tracking (Sentry)
- Add metrics (Prometheus)
- Distributed tracing (OpenTelemetry)

### 3. Testing
- Add unit test coverage
- Integration tests for critical paths
- Load testing for rate limits

### 4. Type Safety
- Complete migration to Pydantic v2
- Remove legacy dict-based sessions
- Add mypy type checking

### 5. Feature Flags
- Enable/disable features dynamically
- A/B testing for new prompts
- Gradual rollout of changes

---

## Summary

Mededbot is a well-architected multilingual medical chatbot with:

✅ **Clear Separation of Concerns**: Handlers, services, utilities, models
✅ **Robust Error Handling**: Circuit breakers, retries, graceful degradation
✅ **Thread Safety**: Locks for shared state, async-aware logging
✅ **Performance**: Background tasks, connection pooling, memory storage
✅ **Security**: Input validation, signature verification, sanitization
✅ **Scalability**: Stateless design, bounded thread pools, rate limiting

The codebase follows Python best practices with async/await, context managers, decorators, and type hints (Pydantic). The architecture is production-ready with comprehensive error handling and monitoring capabilities.
