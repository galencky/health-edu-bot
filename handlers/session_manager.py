sessions: dict[str, dict] = {}

def get_user_session(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "started": False,
            "mode": None,                       # "edu" | "chat"
            "zh_output": None,
            "translated_output": None,
            "translated": False,
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,
            "last_topic": None,
            "last_translation_lang": None,
            "references": None,                # <<< added here
            # MedChat-specific
            "awaiting_chat_language": False,
            "chat_target_lang": None,
        }
    return sessions[user_id]
