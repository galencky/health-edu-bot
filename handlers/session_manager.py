# === handlers/session_manager.py  (only the dict literal) =============

sessions: dict[str, dict] = {}

def get_user_session(user_id: str) -> dict:
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
