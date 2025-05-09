sessions: dict[str, dict] = {}

def get_user_session(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "started": False,
            "zh_output": None,
            "translated_output": None,
            "translated": False,
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,
        }
    return sessions[user_id]
