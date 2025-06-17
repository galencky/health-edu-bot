"""
Session Manager - Thread-Safe User Session Management
"""
import threading
from datetime import datetime, timedelta
from typing import Dict

# Configuration
SESSION_EXPIRY_HOURS = 24

# Storage
_sessions: Dict[str, Dict] = {}
_session_last_access: Dict[str, datetime] = {}
_session_locks: Dict[str, threading.RLock] = {}
_global_lock = threading.RLock()

def get_user_session(user_id: str) -> Dict:
    """Get or create a user session"""
    with _global_lock:
        if user_id not in _sessions:
            _sessions[user_id] = {}
            _session_locks[user_id] = threading.RLock()
        
        _session_last_access[user_id] = datetime.now()
        return _sessions[user_id]

def get_session_lock(user_id: str) -> threading.RLock:
    """Get the lock for a specific user session"""
    with _global_lock:
        return _session_locks.get(user_id, _global_lock)

def reset_user_session(user_id: str) -> None:
    """Reset a user's session to initial state"""
    with _global_lock:
        _sessions[user_id] = {}
        _session_last_access[user_id] = datetime.now()
        
        if user_id not in _session_locks:
            _session_locks[user_id] = threading.RLock()

def cleanup_expired_sessions() -> int:
    """Remove sessions that haven't been accessed in SESSION_EXPIRY_HOURS"""
    with _global_lock:
        now = datetime.now()
        expiry_threshold = timedelta(hours=SESSION_EXPIRY_HOURS)
        
        expired_users = [
            user_id for user_id, last_access in _session_last_access.items()
            if now - last_access > expiry_threshold
        ]
        
        for user_id in expired_users:
            _sessions.pop(user_id, None)
            _session_last_access.pop(user_id, None)
            _session_locks.pop(user_id, None)
        
        return len(expired_users)

def get_session_count() -> int:
    """Get current number of active sessions"""
    with _global_lock:
        return len(_sessions)

# Compatibility alias
get_user_session_sync = get_user_session