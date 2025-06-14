# Bug Fixes Implementation Guide

## Critical Security Fixes

### 1. Remove Hardcoded Secrets

**Immediate Action Required:**
```bash
# 1. Remove .env from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# 2. Force push to remote (coordinate with team)
git push origin --force --all
```

**Update .env.example:**
```env
# .env.example
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_ADDRESS=your_gmail_address_here
GMAIL_APP_PASSWORD=your_gmail_app_password_here
GOOGLE_CREDS_B64=your_base64_encoded_creds_here
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id_here
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here
BASE_URL=https://your-domain.com
DATABASE_URL=postgresql://username:password@host/database?sslmode=require
```

### 2. Fix SQL Injection Vulnerabilities

**File:** `utils/database.py`

Add input validation:
```python
import re
from sqlalchemy import text
from sqlalchemy.sql import bindparam

def validate_user_id(user_id: str) -> str:
    """Validate and sanitize user ID"""
    if not user_id or not isinstance(user_id, str):
        raise ValueError("Invalid user ID")
    
    # LINE user IDs are alphanumeric with specific format
    if not re.match(r'^U[0-9a-f]{32}$', user_id):
        raise ValueError("Invalid LINE user ID format")
    
    return user_id

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize text input"""
    if not text:
        return ""
    
    # Remove null bytes and control characters
    text = text.replace('\x00', '')
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Truncate to max length
    return text[:max_length]

# Update log functions
async def log_chat_to_db(user_id, message, reply, action_type=None, gemini_call=False, gemini_output_url=None):
    """Log chat interaction to database asynchronously with validation"""
    try:
        # Validate inputs
        user_id = validate_user_id(user_id)
        message = sanitize_text(message, 1000)
        reply = sanitize_text(reply, 1000)
        action_type = sanitize_text(action_type, 100) if action_type else None
        
        async with get_async_db_session() as session:
            log = ChatLog(
                user_id=user_id,
                message=message,
                reply=reply,
                action_type=action_type,
                gemini_call=gemini_call,
                gemini_output_url=gemini_output_url
            )
            session.add(log)
            await session.commit()
            return True
    except ValueError as e:
        print(f"❌ [DB] Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ [DB] Failed to log chat: {e}")
        return False
```

### 3. Fix Session Race Conditions

**File:** `handlers/session_manager.py`

Implement proper thread-safe session management:
```python
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from contextlib import asynccontextmanager, contextmanager

class SessionManager:
    """Thread-safe session manager with proper async/sync support"""
    
    def __init__(self, expiry_hours: int = 24):
        self._sessions: Dict[str, Dict] = {}
        self._last_access: Dict[str, datetime] = {}
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.RLock()  # Use RLock for reentrant locking
        self._expiry_hours = expiry_hours
        
    def _create_new_session(self) -> dict:
        """Create a new session with default values"""
        return {
            "started": False,
            "mode": None,
            "zh_output": None,
            "translated_output": None,
            "translated": False,
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,
            "last_topic": None,
            "last_translation_lang": None,
            "references": None,
            "awaiting_chat_language": False,
            "chat_target_lang": None,
            "awaiting_stt_translation": False,
            "stt_transcription": None,
            "stt_last_translation": None,
            "tts_audio_url": None,
            "tts_audio_dur": 0,
            "tts_queue": [],
            "_prev_mode": None,
        }
    
    @asynccontextmanager
    async def get_session_async(self, user_id: str):
        """Get session with async lock"""
        async with self._async_lock:
            self._last_access[user_id] = datetime.now()
            if user_id not in self._sessions:
                self._sessions[user_id] = self._create_new_session()
            yield self._sessions[user_id]
    
    @contextmanager
    def get_session_sync(self, user_id: str):
        """Get session with sync lock"""
        with self._sync_lock:
            self._last_access[user_id] = datetime.now()
            if user_id not in self._sessions:
                self._sessions[user_id] = self._create_new_session()
            yield self._sessions[user_id]
    
    async def cleanup_expired_async(self):
        """Async cleanup of expired sessions"""
        async with self._async_lock:
            self._cleanup_expired_internal()
    
    def cleanup_expired_sync(self):
        """Sync cleanup of expired sessions"""
        with self._sync_lock:
            self._cleanup_expired_internal()
    
    def _cleanup_expired_internal(self):
        """Internal cleanup logic"""
        now = datetime.now()
        expired_users = [
            user_id for user_id, last_access in self._last_access.items()
            if now - last_access > timedelta(hours=self._expiry_hours)
        ]
        
        for user_id in expired_users:
            # Clean up large data before removing session
            if user_id in self._sessions:
                session = self._sessions[user_id]
                # Clear large text fields
                session["zh_output"] = None
                session["translated_output"] = None
                session["references"] = None
                session["tts_queue"] = []
            
            self._sessions.pop(user_id, None)
            self._last_access.pop(user_id, None)
        
        if expired_users:
            print(f"Cleaned up {len(expired_users)} expired sessions")

# Global session manager instance
_session_manager = SessionManager()

# Compatibility functions
def get_user_session(user_id: str) -> dict:
    """Get user session (sync version for compatibility)"""
    with _session_manager.get_session_sync(user_id) as session:
        return session

async def get_user_session_async(user_id: str) -> dict:
    """Get user session (async version)"""
    async with _session_manager.get_session_async(user_id) as session:
        return session

def cleanup_expired_sessions():
    """Cleanup expired sessions (sync)"""
    _session_manager.cleanup_expired_sync()
```

### 4. Fix File Operation Security

**File:** `handlers/line_handler.py`

Add proper filename validation:
```python
import os
import re
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Remove any path separators
    filename = os.path.basename(filename)
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Remove multiple dots to prevent extension confusion
    filename = re.sub(r'\.+', '.', filename)
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"
    
    return filename

def save_audio_file(message_content, user_id: str, timestamp: str) -> Path:
    """Safely save audio file with validation"""
    # Validate user_id
    if not re.match(r'^U[0-9a-f]{32}$', user_id):
        raise ValueError("Invalid user ID")
    
    # Sanitize timestamp
    timestamp = re.sub(r'[^\d_]', '', timestamp)
    
    # Create safe filename
    filename = f"{user_id}_{timestamp}.m4a"
    filename = sanitize_filename(filename)
    
    # Ensure save directory exists and is correct
    save_dir = VOICEMAIL_DIR
    if not save_dir.is_dir():
        raise ValueError("Invalid save directory")
    
    # Resolve to absolute path and ensure it's within allowed directory
    local_filename = save_dir / filename
    local_filename = local_filename.resolve()
    
    # Verify the resolved path is within the allowed directory
    if not str(local_filename).startswith(str(save_dir.resolve())):
        raise ValueError("Path traversal attempt detected")
    
    # Save with size limit enforcement
    total_size = 0
    chunk_size = 8192
    
    with open(local_filename, "wb") as f:
        for chunk in message_content.iter_content(chunk_size=chunk_size):
            if chunk:
                total_size += len(chunk)
                if total_size > MAX_AUDIO_FILE_SIZE:
                    f.close()
                    local_filename.unlink(missing_ok=True)
                    raise ValueError(f"File too large: {total_size} bytes")
                f.write(chunk)
    
    return local_filename
```

### 5. Add Security Headers and Rate Limiting

**File:** `main.py`

Add security middleware:
```python
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Add CORS with restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://line.me"],  # Only allow LINE
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["X-Line-Signature"],
)

# Add trusted host validation
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[os.getenv("ALLOWED_HOST", "*")]
)

# Add rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Update webhook with rate limiting
@webhook_router.post("/webhook")
@limiter.limit("30/minute")  # 30 requests per minute
async def webhook(request: Request, x_line_signature: str = Header(None)):
    # Validate signature first
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    body = await request.body()
    
    # Add request size limit (1MB)
    if len(body) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="Request too large")
    
    try:
        body_str = body.decode()
        handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        # Log security event
        print(f"[SECURITY] Invalid signature from IP: {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid signature")
    except Exception as e:
        # Don't expose internal errors
        print(f"[WEBHOOK ERROR] {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail="Bad request")
    
    return "OK"
```

### 6. Fix Email Validation

**File:** `handlers/logic_handler.py`

Strengthen email validation:
```python
import re
import dns.resolver
from email.utils import parseaddr
from email.headerregistry import Address
import hashlib
import hmac

class EmailValidator:
    """Secure email validation with rate limiting"""
    
    def __init__(self):
        self._email_pattern = re.compile(
            r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}@'
            r'[a-zA-Z0-9][a-zA-Z0-9.-]{0,62}\.[a-zA-Z]{2,}$'
        )
        self._sent_emails = {}  # Track sent emails for rate limiting
        
    def validate_email(self, email: str) -> tuple[bool, str]:
        """Validate email with multiple checks"""
        # Basic format check
        if not self._email_pattern.match(email):
            return False, "Invalid email format"
        
        # Length check
        if len(email) > 254:  # RFC 5321
            return False, "Email too long"
        
        # Parse email
        try:
            parsed_name, parsed_email = parseaddr(email)
            if parsed_email != email:
                return False, "Invalid email format"
        except Exception:
            return False, "Invalid email format"
        
        # Check for common typos
        domain = email.split('@')[1].lower()
        common_domains = {
            'gmial.com': 'gmail.com',
            'gmai.com': 'gmail.com',
            'yahooo.com': 'yahoo.com',
            'outlok.com': 'outlook.com'
        }
        if domain in common_domains:
            return False, f"Did you mean @{common_domains[domain]}?"
        
        # Check MX records
        try:
            dns.resolver.resolve(domain, 'MX', lifetime=3)
        except Exception:
            return False, "Email domain cannot receive mail"
        
        # Rate limiting check
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        now = time.time()
        
        if email_hash in self._sent_emails:
            last_sent = self._sent_emails[email_hash]
            if now - last_sent < 300:  # 5 minutes
                return False, "Please wait 5 minutes before sending another email"
        
        self._sent_emails[email_hash] = now
        
        # Clean old entries
        self._sent_emails = {
            h: t for h, t in self._sent_emails.items()
            if now - t < 3600  # Keep for 1 hour
        }
        
        return True, "Valid"

# Global validator instance
email_validator = EmailValidator()
```

### 7. Implement Proper Authentication

**File:** `middleware/auth.py` (new file)

```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from datetime import datetime, timedelta

class LineAuthMiddleware:
    """Verify LINE webhook signatures and user authentication"""
    
    def __init__(self):
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        if not self.channel_secret:
            raise ValueError("LINE_CHANNEL_SECRET not configured")
    
    async def verify_webhook(self, request: Request, signature: str):
        """Verify LINE webhook signature"""
        body = await request.body()
        
        # Create signature
        hash = hmac.new(
            self.channel_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        calculated_signature = base64.b64encode(hash).decode('utf-8')
        
        # Timing-safe comparison
        if not hmac.compare_digest(signature, calculated_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        return body

class JWTBearer(HTTPBearer):
    """JWT authentication for internal endpoints"""
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.secret = os.getenv("JWT_SECRET", "change-this-secret")
    
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid or expired token")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code")
    
    def verify_jwt(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
```

## Implementation Priority

1. **Day 1 - Critical Security**
   - Remove hardcoded secrets
   - Rotate all credentials
   - Fix SQL injection risks

2. **Day 2 - Session & File Security**
   - Implement thread-safe sessions
   - Fix file operation vulnerabilities
   - Add input validation

3. **Day 3 - API Security**
   - Add authentication
   - Implement rate limiting
   - Add security headers

4. **Week 1 - Complete Security Hardening**
   - Fix all HIGH severity issues
   - Add comprehensive logging
   - Implement monitoring

5. **Week 2 - Code Quality**
   - Fix MEDIUM severity issues
   - Add unit tests
   - Documentation updates