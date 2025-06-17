"""
Session Manager - Thread-Safe User Session Management
Handles user sessions with proper locking to prevent race conditions
"""
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from contextlib import contextmanager

# ============================================================
# CONFIGURATION
# ============================================================

SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours of inactivity
MAX_SESSIONS = 10000       # Maximum concurrent sessions
LOG_PREFIX = "[SESSION]"   # Logging prefix

# ============================================================
# STORAGE
# ============================================================

# Session data storage
_sessions: Dict[str, Dict] = {}
_session_last_access: Dict[str, datetime] = {}
_session_locks: Dict[str, threading.RLock] = {}

# Thread safety
_global_lock = threading.RLock()  # For session creation/deletion

# ============================================================
# SESSION TEMPLATE
# ============================================================

def create_new_session() -> Dict:
    """
    Create a new session with all required fields initialized
    
    Session structure:
    - Core: started, mode
    - Education: zh_output, translated_output, references, etc.
    - Chat: chat_target_lang, awaiting_chat_language
    - STT/TTS: transcription, audio URLs, etc.
    """
    return {
        # Core fields
        "started": False,
        "mode": None,  # "edu" | "chat" | None
        
        # Education mode fields
        "zh_output": None,
        "translated_output": None,
        "translated": False,
        "awaiting_translate_language": False,
        "awaiting_email": False,
        "awaiting_modify": False,
        "last_topic": None,
        "last_translation_lang": None,
        "references": None,
        
        # Chat mode fields
        "awaiting_chat_language": False,
        "chat_target_lang": None,
        
        # STT (Speech-to-Text) fields
        "awaiting_stt_translation": False,
        "stt_transcription": None,
        "stt_last_translation": None,
        
        # TTS (Text-to-Speech) fields
        "tts_audio_url": None,
        "tts_audio_dur": 0,
        "tts_queue": [],
        
        # State management
        "_prev_mode": None,  # Remember mode before STT interruption
    }

# ============================================================
# CORE FUNCTIONS
# ============================================================

def get_user_session(user_id: str) -> Dict:
    """
    Get or create a user session
    
    Thread-safe: Uses global lock for creation, per-session lock for access
    
    Args:
        user_id: Unique user identifier
        
    Returns:
        Session dictionary for the user
    """
    with _global_lock:
        # Create session if doesn't exist
        if user_id not in _sessions:
            _sessions[user_id] = create_new_session()
            _session_locks[user_id] = threading.RLock()
            print(f"{LOG_PREFIX} Created new session for user: {user_id[:10]}...")
        
        # Update last access time
        _session_last_access[user_id] = datetime.now()
        
        return _sessions[user_id]


def get_session_lock(user_id: str) -> threading.RLock:
    """
    Get the lock for a specific user session
    
    Use this when modifying session data to prevent race conditions:
    
    Example:
        session = get_user_session(user_id)
        lock = get_session_lock(user_id)
        with lock:
            session['field'] = value
    """
    with _global_lock:
        return _session_locks.get(user_id, _global_lock)


@contextmanager
def session_context(user_id: str):
    """
    Context manager for safe session access
    
    Example:
        with session_context(user_id) as session:
            session['field'] = value
    """
    session = get_user_session(user_id)
    lock = get_session_lock(user_id)
    with lock:
        yield session


def reset_user_session(user_id: str) -> None:
    """Reset a user's session to initial state"""
    with _global_lock:
        _sessions[user_id] = create_new_session()
        _session_last_access[user_id] = datetime.now()
        
        # Ensure lock exists
        if user_id not in _session_locks:
            _session_locks[user_id] = threading.RLock()
        
        print(f"{LOG_PREFIX} Reset session for user: {user_id[:10]}...")

# ============================================================
# CLEANUP FUNCTIONS
# ============================================================

def cleanup_expired_sessions() -> int:
    """
    Remove sessions that haven't been accessed in SESSION_EXPIRY_HOURS
    
    Returns:
        Number of sessions removed
    """
    with _global_lock:
        now = datetime.now()
        expiry_threshold = timedelta(hours=SESSION_EXPIRY_HOURS)
        
        # Find expired sessions
        expired_users = [
            user_id for user_id, last_access in _session_last_access.items()
            if now - last_access > expiry_threshold
        ]
        
        # Remove expired sessions
        for user_id in expired_users:
            _sessions.pop(user_id, None)
            _session_last_access.pop(user_id, None)
            _session_locks.pop(user_id, None)
        
        if expired_users:
            print(f"{LOG_PREFIX} Cleaned up {len(expired_users)} expired sessions")
        
        return len(expired_users)

# ============================================================
# MONITORING FUNCTIONS
# ============================================================

def get_session_stats() -> Dict:
    """Get statistics about current sessions"""
    with _global_lock:
        total_sessions = len(_sessions)
        
        # Count by mode
        mode_counts = {"edu": 0, "chat": 0, "none": 0}
        active_count = 0
        
        for session in _sessions.values():
            mode = session.get("mode", "none") or "none"
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            
            if session.get("started"):
                active_count += 1
        
        return {
            "total": total_sessions,
            "active": active_count,
            "by_mode": mode_counts,
            "oldest_access": min(_session_last_access.values()) if _session_last_access else None,
            "newest_access": max(_session_last_access.values()) if _session_last_access else None,
        }


def get_all_active_sessions() -> Dict[str, datetime]:
    """Get all active sessions with their last access times"""
    with _global_lock:
        return _session_last_access.copy()


def get_session_count() -> int:
    """Get current number of active sessions"""
    with _global_lock:
        return len(_sessions)

# ============================================================
# ASYNC WRAPPERS
# ============================================================

async def get_user_session_async(user_id: str) -> Dict:
    """Async wrapper for get_user_session"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_user_session, user_id)


async def cleanup_expired_sessions_async() -> int:
    """Async wrapper for cleanup_expired_sessions"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, cleanup_expired_sessions)

# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

# For backward compatibility
get_user_session_sync = get_user_session

# ============================================================
# USAGE EXAMPLES
# ============================================================

"""
Example 1: Simple session access
    session = get_user_session(user_id)
    session['mode'] = 'edu'

Example 2: Thread-safe modification
    session = get_user_session(user_id)
    lock = get_session_lock(user_id)
    with lock:
        session['counter'] = session.get('counter', 0) + 1

Example 3: Using context manager
    with session_context(user_id) as session:
        session['field'] = value
        
Example 4: Monitoring
    stats = get_session_stats()
    print(f"Active sessions: {stats['active']}/{stats['total']}")
"""