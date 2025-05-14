"""Top-level dispatcher for both Education and MedChat branches.

All business logic lives here; front-end handlers (LINE, /chat, …)
just call `handle_user_message()` and log the returned flag.

Returns
-------
tuple[str, bool]
    reply_text, gemini_called   (True iff this function invoked Gemini)
"""

from __future__ import annotations
import re, dns.resolver
from typing import Tuple

# Gemini helpers
from services.gemini_service import (
    call_zh,
    call_translate,
    plainify,
    confirm_translate,
)
from services.prompt_config import modify_prompt

# Command words
from utils.command_sets import (
    new_commands, edu_commands, chat_commands,
    modify_commands, translate_commands, mail_commands,
)

# Other helpers
from handlers.mail_handler     import send_last_txt_email
from handlers.medchat_handler  import handle_medchat


# ──────────────────────────────────────────────────────────────────────
def _has_mx_record(domain: str) -> bool:
    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=3))
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────
def handle_user_message(user_id: str, text: str, session: dict) -> Tuple[str, bool]:
    """Route a single incoming message."""
    gemini_called = False                     # ← new flag
    raw           = text.strip()
    text_lower    = raw.lower()

    # 0 ───── NEW conversation ─────────────────────────────────────────
    if not session.get("started"):
        if text_lower in new_commands:
            _reset_session(session)
            return (
                "🆕 新對話開始。\n請輸入以下其一以選擇模式：\n"
                "• ed / education / 衛教 → 產生衛教單張\n"
                "• chat / 聊天 → 醫療即時翻譯 (MedChat)",
                gemini_called,
            )
        return "⚠️ 請先輸入 new / 開始 啟動對話。", gemini_called

    # 1 ───── Mode selection ───────────────────────────────────────────
    if session.get("mode") is None:
        if text_lower in edu_commands:
            session["mode"] = "edu"
            return "✅ 已進入『衛教』模式，請輸入：疾病名稱 + 衛教主題。", gemini_called
        if text_lower in chat_commands:
            session["mode"] = "chat"
            session["awaiting_chat_language"] = True
            return "🌐 請輸入欲翻譯到的語言，例如：英文、日文…", gemini_called
        return "⚠️ 未辨識模式，請輸入 ed 或 chat。", gemini_called

    # 2 ───── Chat branch ──────────────────────────────────────────────
    if session["mode"] == "chat":
        if text_lower in new_commands:         # restart inside chat
            _reset_session(session)
            return (
                "🆕 新對話開始。\n請輸入以下其一以選擇模式：\n"
                "• ed / education / 衛教 → 產生衛教單張\n"
                "• chat / 聊天 → 醫療即時翻譯 (MedChat)",
                gemini_called,
            )
        if text_lower in edu_commands:
            return "⚠️ 目前在『聊天』模式。如要切換到衛教請先輸入 new。", gemini_called

        # delegate to MedChat handler (it calls plainify / confirm_translate)
        reply, _ = handle_medchat(user_id, raw, session)
        # handle_medchat itself calls Gemini → flag True
        gemini_called = True
        return reply, gemini_called

    # 3 ───── Education branch ─────────────────────────────────────────
    if text_lower in chat_commands:
        return "⚠️ 目前在『衛教』模式。如要切換到聊天請先輸入 new。", gemini_called

    # Convenience flags
    is_new        = text_lower in new_commands
    is_translate  = text_lower in translate_commands
    is_mail       = text_lower in mail_commands
    is_modify_cmd = text_lower in modify_commands

    if sum([is_new, is_translate, is_mail, is_modify_cmd]) > 1:
        return "⚠️ 同時偵測到多個指令，請一次只執行一項：new/modify/translate/mail。", gemini_called

    # --- new/reset inside edu -----------------------------------------
    if is_new:
        _reset_session(session)
        return (
            "🆕 已重新開始。\n"
            "請輸入以下其一以選擇模式：\n"
            "• ed / education / 衛教 → 產生衛教單張\n"
            "• chat / 聊天 → 醫療即時翻譯 (MedChat)",
            gemini_called,
        )

    # --- awaiting modify content --------------------------------------
    if session.get("awaiting_modify"):
        gemini_called = True
        prompt  = f"User instruction:\n{raw}\n\nOriginal content:\n{session['zh_output']}"
        new_zh  = call_zh(prompt, system_prompt=modify_prompt)
        session.update({"zh_output": new_zh, "awaiting_modify": False})
        return (
            f"✅ 已修改中文版內容：\n\n{new_zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 修改/modify 再次調整內容\n"
            "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "3️⃣ 輸入: mail/寄送，寄出內容\n"
            "4️⃣ 輸入 new 重新開始\n"
            "⚠️ 請注意: 若進行修改或翻譯需在輸入指令後等待 20 秒左右，請耐心等候回覆...",
            gemini_called,
        )

    # --- enter modify mode --------------------------------------------
    if is_modify_cmd:
        if session.get("translated"):
            return "⚠️ 已進行翻譯，如需重新調整請輸入 new 重新開始。", gemini_called
        if not session.get("zh_output"):
            return "⚠️ 尚未產出中文版內容，無法修改。", gemini_called
        session["awaiting_modify"] = True
        return "✏️ 請輸入您的修改指示，例如：強調飲食控制。", gemini_called

    # --- translate -----------------------------------------------------
    if is_translate:
        if not session.get("zh_output"):
            return "⚠️ 尚未產出中文版內容，請先輸入疾病與主題。", gemini_called
        session["awaiting_translate_language"] = True
        return "🌐 請輸入您要翻譯成的語言，例如：日文、泰文…", gemini_called

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
        return (
            f"🌐 翻譯完成（目標語言：{target_lang}）：\n\n"
            f"原文：\n{zh_text}\n\n譯文：\n{translated}\n\n"
            "您目前可：\n"
            "1️⃣ 再次輸入: 翻譯/translate/trans 進行翻譯\n"
            "2️⃣ 輸入: mail/寄送，寄出內容\n"
            "3️⃣ 輸入 new 重新開始",
            gemini_called,
        )

    # --- mail ----------------------------------------------------------
    if is_mail:
        if not session.get("zh_output"):
            return "⚠️ 尚無內容可寄送，請先產生衛教內容。", gemini_called
        session["awaiting_email"] = True
        return "📧 請輸入您要寄送至的 email 地址：", gemini_called

    if session.get("awaiting_email"):
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        if re.fullmatch(email_pattern, raw):
            domain = raw.split("@")[1]
            if not _has_mx_record(domain):
                return "⚠️ 此 email 網域無法接收郵件，請重新確認。", gemini_called
            session["awaiting_email"] = False
            if send_last_txt_email(user_id, raw, session):
                return f"✅ 已成功寄出衛教內容至 {raw}", gemini_called
            return "⚠️ 寄送失敗，請稍後再試。", gemini_called
        return "⚠️ 無效 email 格式，請重新輸入，例如：example@gmail.com", gemini_called

    # --- generate initial zh-TW sheet ----------------------------------
    if not session.get("zh_output"):
        gemini_called = True
        zh = call_zh(raw)
        session.update({"zh_output": zh, "last_topic": raw[:30]})
        return (
            f"✅ 中文版衛教內容已生成：\n\n{zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 修改/modify 調整內容\n"
            "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "3️⃣ 輸入: mail/寄送，寄出內容\n"
            "4️⃣ 輸入 new 重新開始",
            gemini_called,
        )

    # --- fallback ------------------------------------------------------
    return (
        "⚠️ 指令不明，請依照下列操作：\n"
        "new / 開始           → 重新開始\n"
        "modify / 修改        → 進入修改\n"
        "translate / 翻譯     → 翻譯\n"
        "mail / 寄送          → 寄出內容",
        gemini_called,
    )


# ──────────────────────────────────────────────────────────────────────
def _reset_session(session: dict) -> None:
    """Initialize (or re-initialize) the conversation state."""
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
        # MedChat
        "awaiting_chat_language": False,
        "chat_target_lang": None,
    })
