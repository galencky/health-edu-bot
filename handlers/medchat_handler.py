from services.gemini_service import plainify, confirm_translate
from utils.logging import log_chat
from utils.command_sets import create_quick_reply_items, COMMON_LANGUAGES, CHAT_TTS_OPTIONS

__all__ = ["handle_medchat"]

def _looks_like_language(token: str) -> bool:
    """Heuristic: short word (≤15 chars) w/o punctuation → language name."""
    return (
        1 <= len(token) <= 15 and
        all(ch.isalpha() or "\u4e00" <= ch <= "\u9fff" for ch in token)
    )


def handle_medchat(user_id: str, raw: str, session: dict) -> tuple[str, bool, dict]:
    
    # 1. Waiting for user to supply the target language -----------------
    if session.get("awaiting_chat_language"):
        if not _looks_like_language(raw):
            quick_reply = {
                "items": create_quick_reply_items(COMMON_LANGUAGES)
            }
            return "⚠️ 請先輸入欲翻譯的語言，例如：英文、日文。", False, quick_reply

        session["chat_target_lang"] = raw
        session["awaiting_chat_language"] = False
        # Ensure session remains active
        session["started"] = True
        session["mode"] = "chat"
        return f"✅ 目標語言已設定為「{raw}」。\n請輸入要轉換的文字…", False, None

    # 2. No language set yet -------------------------------------------
    if not session.get("chat_target_lang"):
        session["awaiting_chat_language"] = True
        # Ensure session remains active
        session["started"] = True
        session["mode"] = "chat"
        quick_reply = {
            "items": create_quick_reply_items(COMMON_LANGUAGES)
        }
        return "⚠️ 尚未設定語言，請先輸入目標語言，例如：英文。", False, quick_reply

    # 3. Plain‑ify Chinese, then translate + confirmation --------------
    plain_zh = plainify(raw)
    translated = confirm_translate(plain_zh, session["chat_target_lang"])

    # ── stash for Drive log (upload_gemini_log looks for these keys) ──
    session["zh_output"]         = plain_zh
    session["translated_output"] = translated

    reply_text = (
        "您是否想表達：\n"
        f"{plain_zh}\n\n"
        f"{translated}"
)
    
    quick_reply = {
        "items": create_quick_reply_items(CHAT_TTS_OPTIONS)
    }

    # Log interaction --------------------------------------------------
    log_chat(
        user_id,
        raw,
        reply_text,
        session,
        action_type="medchat",
        gemini_call="yes",
    )

    return reply_text, False, quick_reply
