# utils/paths.py
from pathlib import Path
import threading

BASE_DIR = Path(__file__).resolve().parent.parent   # repo root
VOICEMAIL_DIR = BASE_DIR / "voicemail"
TTS_AUDIO_DIR = BASE_DIR / "tts_audio"
CREDS_PATH    = BASE_DIR / "credentials.json"

# BUG FIX: Thread-safe directory creation
# Previously: Race condition when multiple threads try to create directories
_dir_creation_lock = threading.Lock()

def ensure_directories_exist():
    """Thread-safe directory creation"""
    with _dir_creation_lock:
        for p in (VOICEMAIL_DIR, TTS_AUDIO_DIR):
            try:
                p.mkdir(exist_ok=True, parents=True)
            except OSError as e:
                # Handle rare case where directory was created between check and creation
                if not p.exists():
                    raise e

# Create directories on module import (with thread safety)
ensure_directories_exist()
