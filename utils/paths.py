# utils/paths.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # repo root
VOICEMAIL_DIR = BASE_DIR / "voicemail"
TTS_AUDIO_DIR = BASE_DIR / "tts_audio"
CREDS_PATH    = BASE_DIR / "credentials.json"

for p in (VOICEMAIL_DIR, TTS_AUDIO_DIR):
    p.mkdir(exist_ok=True)
