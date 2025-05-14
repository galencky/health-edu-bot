"""
LINE webhook adapter.
Business logic lives in handlers.logic_handler; this file only:

1. Pulls/creates the user session.
2. Passes the message to handle_user_message().
3. Formats the reply bubbles for LINE.
4. Logs the interaction.

If logic_handler invokes Gemini it returns gemini_called=True,
so we can log appropriately without re-implementing that rule here.
"""

from __future__ import annotations
import os, time
from linebot import LineBotApi
from linebot.models import TextSendMessage

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))


# ---------- helpers -----------------------------------------------------
def _chunks(text: str, limit: int = 4000) -> list[str]:
    """Split long text into ≤4 000-character pieces (LINE hard cap)."""
    return [text[i : i + limit] for i in range(0, len(text), limit)]


# ---------- main entry --------------------------------------------------
def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    t0 = time.time()
    reply, gemini_called = handle_user_message(user_id, user_input, session)
    elapsed = time.time() - t0

    # ---------- build LINE bubbles -------------------------------------
    messages: list[TextSendMessage] = []

    if session.get("mode") == "chat":                    # MedChat
        messages.append(TextSendMessage(text=reply))

    else:                                                # Education branch
        zh = session.get("zh_output") or ""
        tr = session.get("translated_output") or ""

        # show up to three bubbles: max 2 zh + (3-len) tr
        zh_bubbles = _chunks(f"📄 原文：\n{zh}")[:2] if zh else []
        tr_bubbles = _chunks(f"🌐 譯文：\n{tr}")[: max(0, 3 - len(zh_bubbles))] if tr else []

        for txt in (*zh_bubbles, *tr_bubbles):
            messages.append(TextSendMessage(text=txt))

        # always append the action-hint / fallback text returned by logic_handler
        messages.append(TextSendMessage(text=reply))

        # warn if not all text could be shown
        if len(zh_bubbles) + len(tr_bubbles) > 3:
            messages.append(TextSendMessage(
                text="⚠️ 內容過長，僅部分顯示。如需完整內容請輸入 mail / 寄送。"
            ))

    # ---------- send & log ---------------------------------------------
    try:
        line_bot_api.reply_message(event.reply_token, messages)
    except Exception as exc:
        # best-effort fallback to avoid silent failure
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"⚠️ 發生錯誤：{exc}")
        )

    # MedChat 已自行記錄，避免重複
    if session.get("mode") != "chat":
        log_to_sheet(
            user_id,
            user_input,
            reply[:200],
            session,
            action_type="Gemini reply" if gemini_called else "sync reply",
            gemini_call="yes" if gemini_called else "no",
        )