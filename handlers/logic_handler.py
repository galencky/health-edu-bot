"""Top‑level dispatcher for both Education and MedChat branches.

This file replaces the previous logic_handler, integrating the
separate MedChat handler while keeping the original education flow
intact.  All command words are imported from utils.command_sets.
"""

from __future__ import annotations

import re
import dns.resolver
from typing import Tuple

from services.gemini_service import call_zh, call_translate
from utils.command_sets import (
    new_commands,
    edu_commands,
    chat_commands,
    modify_commands,
    translate_commands,
    mail_commands,
)
from handlers.mail_handler import send_last_txt_email
from services.prompt_config import modify_prompt
from handlers.medchat_handler import handle_medchat

# ── helpers ──────────────────────────────────────────────────────────

def _has_mx_record(domain: str) -> bool:
    try:
        records = dns.resolver.resolve(domain, "MX", lifetime=3)
        return len(records) > 0
    except Exception:
        return False


# ── main entry point ────────────────────────────────────────────────

def handle_user_message(user_id: str, text: str, session: dict) -> Tuple[str, bool]:
    """Route a single incoming LINE message.

    Returns (reply_text, should_call_gemini) but we always perform the
    Gemini work synchronously here, so the second value is *False*.
    """

    raw       = text.strip()
    text_lower = raw.lower()

    # 0. NEW conversation -------------------------------------------------
    if not session.get("started"):
        if text_lower in new_commands:
            _reset_session(session)
            return (
                "🆕 新對話開始。\n請輸入以下其一以選擇模式：\n"
                "• ed / education / 衛教 → 產生衛教單張\n"
                "• chat / 聊天 → 醫療即時翻譯 (MedChat)",
                False,
            )
        return "⚠️ 請先輸入 new / 開始 啟動對話。", False

    # 1. Choose mode right after NEW --------------------------------------
    if session.get("mode") is None:
        if text_lower in edu_commands:
            session["mode"] = "edu"
            return "✅ 已進入『衛教』模式，請輸入：疾病名稱 + 衛教主題。", False
        if text_lower in chat_commands:
            session["mode"] = "chat"
            session["awaiting_chat_language"] = True
            return "🌐 請輸入欲翻譯到的語言，例如：英文、日文…", False
        return "⚠️ 未辨識模式，請輸入 ed 或 chat。", False

    # 2. Dispatch by mode --------------------------------------------------
    if session["mode"] == "chat":

        # NEW inside chat  ←←  add this block
        if text_lower in new_commands:
            _reset_session(session)
            return (
                "🆕 新對話開始。\n請輸入以下其一以選擇模式：\n"
                "• ed / education / 衛教 → 產生衛教單張\n"
                "• chat / 聊天 → 醫療即時翻譯 (MedChat)",
                False,
            )

        # guard: prevent accidental edu command inside chat
        if text_lower in edu_commands:
            return "⚠️ 目前在『聊天』模式。如要切換到衛教請先輸入 new。", False

        return handle_medchat(user_id, raw, session)


    # ---------------- Education branch below -----------------------------

    # quick guard: prevent chat command inside edu
    if text_lower in chat_commands:
        return "⚠️ 目前在『衛教』模式。如要切換到聊天請先輸入 new。", False

    # convenience boolean flags -------------------------------------------
    is_new        = text_lower in new_commands
    is_translate  = text_lower in translate_commands
    is_mail       = text_lower in mail_commands
    is_modify_cmd = text_lower in modify_commands

    if sum([is_new, is_translate, is_mail, is_modify_cmd]) > 1:
        return "⚠️ 同時偵測到多個指令，請一次只執行一項：new/modify/translate/mail。", False

    # NEW inside edu branch (reset) ---------------------------------------
    if is_new:
        _reset_session(session)
        return (
            "🆕 已重新開始。\n請輸入 ed 或 chat 選擇模式。",
            False,
        )

    # Awaiting modify content ---------------------------------------------
    if session.get("awaiting_modify"):
        prompt = f"User instruction:\n{raw}\n\nOriginal content:\n{session['zh_output']}"
        new_zh = call_zh(prompt, system_prompt=modify_prompt)
        session.update({"zh_output": new_zh, "awaiting_modify": False})
        return (
            f"✅ 已修改中文版內容：\n\n{new_zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 修改/modify 再次調整內容\n"
            "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "3️⃣ 輸入: mail/寄送，寄出內容\n"
            "4️⃣ 輸入 new 重新開始\n"
            "⚠️ 請注意: 若進行修改或翻譯需在輸入指令後等待 20 秒左右，請耐心等候回覆...",
            False,
        )

    # Enter modify mode ----------------------------------------------------
    if is_modify_cmd:
        if session.get("translated"):
            return "⚠️ 已進行翻譯，如需重新調整請輸入 new 重新開始。", False
        if not session.get("zh_output"):
            return "⚠️ 尚未產出中文版內容，無法修改。", False
        session["awaiting_modify"] = True
        return "✏️ 請輸入您的修改指示，例如：強調飲食控制。", False

    # Translate ------------------------------------------------------------
    if is_translate:
        if not session.get("zh_output"):
            return "⚠️ 尚未產出中文版內容，請先輸入疾病與主題。", False
        session["awaiting_translate_language"] = True
        return "🌐 請輸入您要翻譯成的語言，例如：日文、泰文…", False

    if session.get("awaiting_translate_language"):
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
            False,
        )

    # Mail -----------------------------------------------------------------
    if is_mail:
        if not session.get("zh_output"):
            return "⚠️ 尚無內容可寄送，請先產生衛教內容。", False
        session["awaiting_email"] = True
        return "📧 請輸入您要寄送至的 email 地址：", False

    if session.get("awaiting_email"):
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        if re.fullmatch(email_pattern, raw):
            domain = raw.split("@")[1]
            if not _has_mx_record(domain):
                return "⚠️ 此 email 網域無法接收郵件，請重新確認。", False
            session["awaiting_email"] = False
            success = send_last_txt_email(user_id, raw, session)
            if success:
                return f"✅ 已成功寄出衛教內容至 {raw}", False
            return "⚠️ 寄送失敗，請稍後再試。", False
        return "⚠️ 無效 email 格式，請重新輸入，例如：example@gmail.com", False

    # Generate zh‑TW education sheet --------------------------------------
    if not session.get("zh_output"):
        zh = call_zh(raw)
        session.update({"zh_output": zh, "last_topic": raw[:30]})
        return (
            f"✅ 中文版衛教內容已生成：\n\n{zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 修改/modify 調整內容\n"
            "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "3️⃣ 輸入: mail/寄送，寄出內容\n"
            "4️⃣ 輸入 new 重新開始",
            False,
        )

    # Fallback -------------------------------------------------------------
    return (
        "⚠️ 指令不明，請依照下列操作：\n"
        "new / 開始           → 重新開始\n"
        "modify / 修改        → 進入修改\n"
        "translate / 翻譯     → 翻譯\n"
        "mail / 寄送          → 寄出內容",
        False,
    )


# ── internal ----------------------------------------------------------

def _reset_session(session: dict) -> None:
    """Clear all state fields and prepare for fresh mode selection."""
    session.clear()
    session.update({
        "started": True,
        "mode": None,
        # Education branch
        "zh_output": None,
        "translated_output": None,
        "translated": False,
        "awaiting_translate_language": False,
        "awaiting_email": False,
        "awaiting_modify": False,
        "last_topic": None,
        "last_translation_lang": None,
        # MedChat branch
        "awaiting_chat_language": False,
        "chat_target_lang": None,
    })
