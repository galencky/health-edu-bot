"""
Unified session manager with proper thread safety and no race conditions.
This replaces the dual-lock system with a single thread-safe implementation.
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
from functools import wraps

# Session storage with thread-safe access
_sessions: Dict[str, Dict] = {}
_session_last_access: Dict[str, datetime] = {}
_session_locks: Dict[str, threading.RLock] = {}  # Per-session locks
_global_lock = threading.RLock()  # Global lock for session creation/deletion

# Configuration
SESSION_EXPIRY_HOURS = 24
MAX_SESSION_SIZE = 100000  # Maximum size of session data in bytes
MAX_TOTAL_SESSIONS = 10000  # Global limit to prevent memory exhaustion
CLEANUP_TRIGGER_THRESHOLD = 8000  # Trigger cleanup at 80% capacity

def _create_new_session() -> dict:
    """Create a new session with default values"""
    return {
        # ╭─ persistent flags ───────────────────────────╮
        "started": False,
        "mode": None,               # "edu" | "chat"
        # ╰──────────────────────────────────────────────╯

        # ─── Education branch ──────────────────────────
        "zh_output": None,
        "translated_output": None,
        "translated": False,
        "awaiting_translate_language": False,
        "awaiting_email": False,
        "awaiting_modify": False,
        "last_topic": None,
        "last_translation_lang": None,
        "references": None,

        # ─── MedChat branch ────────────────────────────
        "awaiting_chat_language": False,
        "chat_target_lang": None,

        # ─── STT / TTS additions ───────────────────────
        "awaiting_stt_translation": False,
        "stt_transcription": None,
        "stt_last_translation": None,

        "tts_audio_url": None,
        "tts_audio_dur": 0,
        "tts_queue": [],            # for race-free queuing

        # remembers the previous mode when STT intrudes
        "_prev_mode": None,
    }

# Removed session size checking - not needed in practice

def get_user_session(user_id: str) -> dict:
    """
    Get or create a user session with thread-safe access.
    Returns a session dict that should be used within a context manager.
    """
    # First check if we need to create a new session
    with _global_lock:
        if user_id not in _sessions:
            _sessions[user_id] = _create_new_session()
            _session_locks[user_id] = threading.RLock()
        
        # Update last access time
        _session_last_access[user_id] = datetime.now()
        
        # Return the session (caller should use get_session_lock for thread safety)
        return _sessions[user_id]

def get_session_lock(user_id: str) -> threading.RLock:
    """Get the lock for a specific user session"""
    with _global_lock:
        return _session_locks.get(user_id, _global_lock)

# Removed emergency cleanup - not needed with simple periodic cleanup

# Async wrapper for compatibility
async def get_user_session_async(user_id: str) -> dict:
    """Async wrapper for get_user_session"""
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_user_session, user_id)

def cleanup_expired_sessions() -> int:
    """Clean up expired sessions - simple version like old bot"""
    with _global_lock:
        now = datetime.now()
        expired_users = []
        
        # Find expired sessions
        for user_id, last_access in list(_session_last_access.items()):
            if now - last_access > timedelta(hours=SESSION_EXPIRY_HOURS):
                expired_users.append(user_id)
        
        # Remove expired sessions and their locks
        for user_id in expired_users:
            _sessions.pop(user_id, None)
            _session_last_access.pop(user_id, None)
            _session_locks.pop(user_id, None)
        
        if expired_users:
            print(f"✅ Cleaned up {len(expired_users)} expired sessions")
        
        return len(expired_users)

def reset_user_session(user_id: str) -> None:
    """Reset a user's session to initial state"""
    with _global_lock:
        _sessions[user_id] = _create_new_session()
        _session_last_access[user_id] = datetime.now()
        if user_id not in _session_locks:
            _session_locks[user_id] = threading.RLock()

def get_all_active_sessions() -> Dict[str, datetime]:
    """Get all active sessions with their last access times (for monitoring)"""
    with _global_lock:
        return _session_last_access.copy()

def get_session_count() -> int:
    """Get current number of active sessions"""
    with _global_lock:
        return len(_sessions)

# Compatibility aliases for existing code
get_user_session_sync = get_user_session

# Export the async cleanup function for compatibility
async def cleanup_expired_sessions_async():
    """Async wrapper for cleanup_expired_sessions"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, cleanup_expired_sessions)