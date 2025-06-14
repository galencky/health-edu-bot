# === handlers/session_manager.py =============
# IMPORTANT: This file now uses a unified thread-safe implementation
# to fix race conditions between async and sync access

# Re-export everything from the new implementation
from .session_manager_v2 import (
    get_user_session,
    get_user_session_sync,
    cleanup_expired_sessions,
    reset_user_session,
    get_all_active_sessions,
    get_session_count,
    SESSION_EXPIRY_HOURS,
)

# The new implementation handles both sync and async access
# so we don't need separate async wrappers anymore