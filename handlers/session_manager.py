# === handlers/session_manager.py  (only the dict literal) =============

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

# BUG FIX: Thread-safe session management with asyncio lock
# Previously: Global dict without synchronization caused race conditions
sessions: Dict[str, Dict] = {}
_session_lock = asyncio.Lock()

# BUG FIX: Session expiration tracking to prevent memory leaks
# Previously: Sessions were never cleaned up, causing unbounded memory growth
_session_last_access: Dict[str, datetime] = {}
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours of inactivity

async def get_user_session(user_id: str) -> dict:
    """
    BUG FIX: Made session access thread-safe with async lock
    Previously: Concurrent access could corrupt session data
    """
    async with _session_lock:
        # Update last access time
        _session_last_access[user_id] = datetime.now()
        
        if user_id not in sessions:
            sessions[user_id] = {
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

                # ─── STT / TTS additions  (NEW) ───────────────
                "awaiting_stt_translation": False,
                "stt_transcription": None,
                "stt_last_translation": None,

                "tts_audio_url": None,
                "tts_audio_dur": 0,
                "tts_queue": [],            # optional: for race-free queuing

                # remembers the previous mode when STT intrudes
                "_prev_mode": None,
            }
        return sessions[user_id]

async def cleanup_expired_sessions():
    """
    BUG FIX: Clean up expired sessions to prevent memory leaks
    Previously: No cleanup mechanism existed
    """
    async with _session_lock:
        now = datetime.now()
        expired_users = []
        
        for user_id, last_access in _session_last_access.items():
            if now - last_access > timedelta(hours=SESSION_EXPIRY_HOURS):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            sessions.pop(user_id, None)
            _session_last_access.pop(user_id, None)
        
        if expired_users:
            print(f"Cleaned up {len(expired_users)} expired sessions")

# Keep the original synchronous function for backward compatibility
def get_user_session(user_id: str) -> dict:
    """
    BUG FIX: This now uses thread-safe access internally
    Previously: Direct dictionary access without synchronization
    """
    # For sync contexts, we need to handle the async lock carefully
    import threading
    
    # Use a thread lock for synchronous contexts
    if not hasattr(get_user_session, '_sync_lock'):
        get_user_session._sync_lock = threading.Lock()
    
    with get_user_session._sync_lock:
        # Update last access time
        _session_last_access[user_id] = datetime.now()
        
        if user_id not in sessions:
            sessions[user_id] = {
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

                # ─── STT / TTS additions  (NEW) ───────────────
                "awaiting_stt_translation": False,
                "stt_transcription": None,
                "stt_last_translation": None,

                "tts_audio_url": None,
                "tts_audio_dur": 0,
                "tts_queue": [],            # optional: for race-free queuing

                # remembers the previous mode when STT intrudes
                "_prev_mode": None,
            }
        return sessions[user_id]
