from services.gemini_service import plainify, confirm_translate
from services.taigi_service import translate_to_taigi, synthesize_taigi
from utils.language_utils import normalize_language_input
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
            return "請先選擇或輸入您需要翻譯的目標語言（支援全球各種語言）：", False, quick_reply

        # Normalize the language input
        normalized_lang = normalize_language_input(raw)
        session["chat_target_lang"] = normalized_lang
        session["awaiting_chat_language"] = False
        # Ensure session remains active
        session["started"] = True
        session["mode"] = "chat"
        
        # Log language selection
        log_message = f"[Language Selection: {normalized_lang}]"
        log_chat(
            user_id,
            log_message,
            f"目標語言已設定為「{normalized_lang}」",
            session,
            action_type="sync reply",
            gemini_call="no"
        )
        
        return f"✅ 目標語言已設定為「{normalized_lang}」。\n請輸入您想翻譯的內容（中文或其他語言皆可）：", False, None

    # 2. No language set yet -------------------------------------------
    if not session.get("chat_target_lang"):
        session["awaiting_chat_language"] = True
        # Ensure session remains active
        session["started"] = True
        session["mode"] = "chat"
        quick_reply = {
            "items": create_quick_reply_items(COMMON_LANGUAGES)
        }
        return "尚未設定翻譯語言。請選擇或輸入您需要的目標語言（支援全球各種語言）：", False, quick_reply

    # 3. Plain‑ify Chinese, then translate + confirmation --------------
    plain_zh = plainify(raw)
    
    # Check if target language is Taiwanese
    target_lang = session["chat_target_lang"]
    if target_lang in ["台語", "臺語", "taiwanese", "taigi"]:
        # Use Taigi service for Taiwanese
        translated = translate_to_taigi(plain_zh)
        gemini_called = "no"
        
        # Generate TTS audio for Taigi
        try:
            audio_url, duration = synthesize_taigi(plain_zh, user_id)
            session["tts_audio_url"] = audio_url
            session["tts_audio_dur"] = duration
            print(f"🎤 [CHAT] Generated Taigi TTS: {audio_url}")
        except Exception as e:
            print(f"[CHAT] Failed to generate Taigi TTS: {e}")
    else:
        # Use Gemini for other languages
        translated = confirm_translate(plain_zh, target_lang)
        gemini_called = "yes"

    # ── stash for Drive log (upload_gemini_log looks for these keys) ──
    session["zh_output"]         = plain_zh
    session["translated_output"] = translated
    session["last_translation_lang"] = target_lang  # Store for TTS

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
        gemini_call=gemini_called,
    )

    return reply_text, False, quick_reply
