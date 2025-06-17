"""
handlers/logic_handler.py

Top-level dispatcher for both Education and MedChat branches.
Front-end handlers (LINE webhook, /chat endpoint, etc.) call
`handle_user_message()` and log the returned flag.

Returns
-------
tuple[str, bool]
    reply_text, gemini_called   (True ↔ this function invoked Gemini)
"""

from __future__ import annotations
import re
import dns.resolver
from typing import Tuple
from services.tts_service import synthesize
from utils.validators import sanitize_text, validate_email, validate_language_code

# ── Gemini helpers ───────────────────────────────────────────────────
from services.gemini_service import (
    call_zh,
    call_translate,
    plainify,
    confirm_translate,
    get_references,   # <<< added
)
from services.prompt_config import modify_prompt

# ── Command words ────────────────────────────────────────────────────
from utils.command_sets import (
    new_commands,
    edu_commands,
    chat_commands,
    modify_commands,
    translate_commands,
    mail_commands,
    speak_commands,
    create_quick_reply_items,
    MODE_SELECTION_OPTIONS,
    COMMON_LANGUAGES,
    COMMON_DISEASES,
    TTS_OPTIONS,
)

# ── Other helpers ────────────────────────────────────────────────────
from handlers.mail_handler import send_last_txt_email
from handlers.medchat_handler import handle_medchat


# ── util ─────────────────────────────────────────────────────────────
def _has_mx_record(domain: str) -> bool:
    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=3))
    except Exception:
        return False

def _create_quick_reply(items):
    """Helper to create quick reply dict"""
    return {"items": create_quick_reply_items(items)}

def _update_references(session, new_refs):
    """Helper to update session references"""
    if new_refs:
        if session.get("references"):
            session["references"].extend(new_refs)
        else:
            session["references"] = new_refs


# ── main dispatcher ─────────────────────────────────────────────────
def handle_user_message(
    user_id: str,
    text: str,
    session: dict,
) -> Tuple[str, bool, dict]:
    """
    Central dispatcher for both Education and MedChat branches.
    Returns (reply_text, gemini_called, quick_reply_data)
    """
    gemini_called = False
    raw           = text.strip()
    text_lower    = raw.lower()
    quick_reply   = None  # Will hold quick reply configuration if needed

    # ──────────────────────────────────────────────────────────────
    # 0. Global “speak / 朗讀” handler  (works in any mode once started)
    # ──────────────────────────────────────────────────────────────
    if session.get("started") and text_lower in speak_commands:

        # 🚫  Block in Education mode
        if session.get("mode") == "edu":
            quick_reply = {
                "items": create_quick_reply_items([("🆕 新對話", "new")])
            }
            return (
                "⚠️ 目前在『衛教』模式，無法語音朗讀。\n"
                "若要使用語音功能請點擊下方按鈕：",
                False,
                quick_reply
            )

        tts_source = session.get("stt_last_translation") \
                  or session.get("translated_output")
        if not tts_source:
            return "⚠️ 尚未有可朗讀的翻譯內容。", False, None

        # BUG FIX: Add error handling for TTS synthesis failures
        # Previously: Uncaught exceptions crashed the webhook
        try:
            url, dur = synthesize(tts_source, user_id)
            session["tts_audio_url"] = url
            session["tts_audio_dur"] = dur
            session.pop("stt_last_translation", None)   # avoid memory leak
            quick_reply = {
                "items": create_quick_reply_items([("🆕 新對話", "new")])
            }
            return "🔊 語音檔已生成", False, quick_reply
        except Exception as e:
            print(f"[TTS ERROR] Failed to synthesize audio: {e}")
            return "⚠️ 語音合成失敗，請稍後再試。", False, None
    
    # Handle continue_translate command
    if session.get("started") and text_lower == "continue_translate":
        if session.get("mode") == "chat" and session.get("chat_target_lang"):
            lang = session.get("chat_target_lang")
            return f"✅ 語言已設定為「{lang}」，請輸入要翻譯的文字：", False, None
        else:
            return "⚠️ 請先進入聊天模式並設定語言。", False, None

    # ──────────────────────────────────────────────────────────────
    # 1. First message guard (“new” required)
    # ──────────────────────────────────────────────────────────────
    if not session.get("started"):
        if text_lower in new_commands:
            _reset_session(session)
            return (
                "🆕 新對話開始。\n請選擇功能或直接傳送語音訊息：",
                gemini_called,
                _create_quick_reply(MODE_SELECTION_OPTIONS)
            )
        quick_reply = _create_quick_reply([("🆕 開始", "new")])
        return "⚠️ 請點擊下方按鈕開始對話：", gemini_called, quick_reply

    # ──────────────────────────────────────────────────────────────
    # 2. Mode selection (after “new”)
    # ──────────────────────────────────────────────────────────────
    if session.get("mode") is None:
        if text_lower in edu_commands:
            session["mode"] = "edu"
            return "✅ 已進入『衛教』模式，請輸入：疾病名稱 + 衛教主題。\n⏳ 生成約需 10-20 秒...", gemini_called, _create_quick_reply([
                ("糖尿病 飲食控制", "糖尿病 飲食控制"),
                ("高血壓 生活習慣", "高血壓 生活習慣"),
                ("心臟病 復健運動", "心臟病 復健運動"),
                ("氣喘 環境控制", "氣喘 環境控制")
            ])
        if text_lower in chat_commands:
            session["mode"] = "chat"
            session["awaiting_chat_language"] = True
            return "🌐 請輸入欲翻譯到的語言，例如：英文、日文…", gemini_called, _create_quick_reply(COMMON_LANGUAGES)
        quick_reply = _create_quick_reply(MODE_SELECTION_OPTIONS)
        return (
            "請選擇功能或直接傳送語音訊息：",
            gemini_called,
            quick_reply
        )
            

    # ──────────────────────────────────────────────────────────────
    # 3. Chat branch  (MED-CHAT)
    # ──────────────────────────────────────────────────────────────
    if session.get("mode") == "chat":

        # “new” while chatting
        if text_lower in new_commands:
            _reset_session(session)
            return (
                "🆕 新對話開始。\n請選擇功能或直接傳送語音訊息：",
                gemini_called,
                _create_quick_reply(MODE_SELECTION_OPTIONS)
            )

        if text_lower in edu_commands:
            quick_reply = {
                "items": create_quick_reply_items([("🆕 新對話", "new")])
            }
            return "⚠️ 目前在『聊天』模式。如要切換到衛教請點擊下方按鈕：", gemini_called, quick_reply

        # delegate to MedChat handler (Gemini inside)
        reply, _, medchat_quick_reply = handle_medchat(user_id, raw, session)
        gemini_called = True
        return reply, gemini_called, medchat_quick_reply

    # 3. Education branch ------------------------------------------------
    if text_lower in chat_commands:
        quick_reply = {
            "items": create_quick_reply_items([("🆕 新對話", "new")])
        }
        return "⚠️ 目前在『衛教』模式。如要切換到聊天請點擊下方按鈕：", gemini_called, quick_reply

    # convenience flags
    is_new        = text_lower in new_commands
    is_translate  = text_lower in translate_commands
    is_mail       = text_lower in mail_commands
    is_modify_cmd = text_lower in modify_commands

    if sum([is_new, is_translate, is_mail, is_modify_cmd]) > 1:
        return "⚠️ 同時偵測到多個指令，請一次只執行一項：new / modify / translate / mail。", gemini_called, None

    # --- NEW / reset ----------------------------------------------------
    if is_new:
        _reset_session(session)
        quick_reply = {
            "items": create_quick_reply_items(MODE_SELECTION_OPTIONS)
        }
        return (
                "🆕 新對話開始。\n請選擇功能或直接傳送語音訊息：",
                gemini_called,
                quick_reply
            )

    # --- awaiting modified content -------------------------------------
    if session.get("awaiting_modify"):
        gemini_called = True
        prompt  = f"User instruction:\n{raw}\n\nOriginal content:\n{session['zh_output']}"
        new_zh  = call_zh(prompt, system_prompt=modify_prompt)
        session.update({"zh_output": new_zh, "awaiting_modify": False})
        new_refs = get_references()
        if new_refs:  # Only log if we have references
            print(f"[DEBUG MODIFY] Found {len(new_refs)} new references after modification")
        _update_references(session, new_refs)
        print(f"[DEBUG MODIFY] Total refs after merge: {len(session.get('references', []))}")
        quick_reply = _create_quick_reply([
            ("✏️ 修改", "modify"),
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])
        return (
            "✅ 已修改中文版內容。",
            gemini_called,
            quick_reply
        )

    # --- enter modify mode ---------------------------------------------
    if is_modify_cmd:
        if session.get("translated"):
            quick_reply = {
                "items": create_quick_reply_items([("🆕 新對話", "new")])
            }
            return "⚠️ 已完成翻譯，若需調整請點擊下方按鈕重新開始：", gemini_called, quick_reply
        if not session.get("zh_output"):
            return "⚠️ 尚未產出中文版內容，無法修改。", gemini_called, None
        session["awaiting_modify"] = True
        return "✏️ 請輸入您的修改指示，例如：強調飲食控制。\n⏳ 處理約需 10-20 秒...", gemini_called, None

    # --- translate ------------------------------------------------------
    if is_translate:
        if not session.get("zh_output"):
            return "⚠️ 尚未產出中文版內容，請先輸入疾病與主題。", gemini_called, None
        session["awaiting_translate_language"] = True
        quick_reply = {
            "items": create_quick_reply_items(COMMON_LANGUAGES)
        }
        return "🌐 請輸入您要翻譯成的語言，例如：日文、泰文…\n⏳ 處理約需 10-20 秒...", gemini_called, quick_reply

    if session.get("awaiting_translate_language"):
        gemini_called = True
        target_lang = raw
        zh_text     = session["zh_output"]
        translated  = call_translate(zh_text, target_lang)
        session.update({
            "translated_output": translated,
            "translated": True,
            "awaiting_translate_language": False,
            "last_translation_lang": target_lang,
            "last_topic": zh_text.split("\n")[0][:20],
        })
        new_refs = get_references()
        _update_references(session, new_refs)
        quick_reply = _create_quick_reply([
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])
        return (
            f"🌐 翻譯完成（目標語言：{target_lang}）。",
            gemini_called,
            quick_reply
        )

    # --- mail -----------------------------------------------------------
    if is_mail:
        if not session.get("zh_output"):
            return "⚠️ 尚無內容可寄送，請先產生衛教內容。", gemini_called, None
        session["awaiting_email"] = True
        return "📧 請輸入您要寄送至的 email 地址：", gemini_called, None

    if session.get("awaiting_email"):
        # Validate email using secure validator
        try:
            validated_email = validate_email(raw)
        except ValueError as e:
            return "⚠️ 無效 email 格式，請重新輸入，例如：example@gmail.com", gemini_called, None
        
        # Check MX record for domain
        domain = validated_email.split("@")[1]
        if not _has_mx_record(domain):
            return "⚠️ 此 email 網域無法接收郵件，請重新確認。", gemini_called, None
            
        session["awaiting_email"] = False
        
        # Send email with validated address
        if send_last_txt_email(user_id, validated_email, session):
            quick_reply = {
                "items": create_quick_reply_items([("🆕 新對話", "new")])
            }
            return f"✅ 已成功寄出衛教內容至 {validated_email}", gemini_called, quick_reply
        return "⚠️ 寄送失敗，請稍後再試。", gemini_called, None

    # --- first-time zh-TW sheet ----------------------------------------
    if not session.get("zh_output"):
        gemini_called = True
        zh = call_zh(raw)
        session.update({"zh_output": zh, "last_topic": raw[:30]})
        new_refs = get_references()
        _update_references(session, new_refs)
        quick_reply = _create_quick_reply([
            ("✏️ 修改", "modify"),
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])
        return (
            "✅ 中文版衛教內容已生成。",
            gemini_called,
            quick_reply
        )

    # --- fallback -------------------------------------------------------
    quick_reply = {
        "items": create_quick_reply_items([
            ("🆕 開始", "new"),
            ("✏️ 修改", "modify"),
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail")
        ])
    }
    return (
        "⚠️ 指令不明。",
        gemini_called,
        quick_reply
    )


# ── session reset helper ─────────────────────────────────────────────
def _reset_session(session: dict) -> None:
    session.clear()
    session.update({
        "started": True,
        "mode": None,

        # Education
        "zh_output": None,
        "translated_output": None,
        "translated": False,
        "awaiting_translate_language": False,
        "awaiting_email": False,
        "awaiting_modify": False,
        "last_topic": None,
        "last_translation_lang": None,
        "references": None,

        # MedChat
        "awaiting_chat_language": False,
        "chat_target_lang": None,

        # STT / TTS
        "awaiting_stt_translation": False,
        "stt_transcription": None,
        "stt_last_translation": None,
        "tts_audio_url": None,
        "tts_audio_dur": 0,
        "tts_queue": [],

        # misc
        "_prev_mode": None,
    })
