"""Reply handler for LINE webhook events.

*   Distinguishes between **education** and **MedChat** modes.
*   Calls Gemini only when necessary (after a mode is chosen).
*   Builds multi‑chunk carousel replies **only** for the education branch.
"""

import os
import time
from linebot import LineBotApi
from linebot.models import TextSendMessage

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------

def split_text(text: str, chunk_size: int = 4000) -> list[str]:
    """Split long text into LINE‑safe chunks (≤4000 chars each)."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def will_call_gemini(text: str, session: dict) -> bool:
    """Decide whether the incoming message requires a Gemini call."""
    text_lower = text.strip().lower()

    # 🚫 1. No Gemini before the user picks a mode
    if session.get("mode") is None:
        return False

    # 🚦 2. Pending operations that always hit Gemini (edu branch)
    if session.get("awaiting_modify") or session.get("awaiting_translate_language"):
        return True

    # 🚦 3. MedChat messages + first edu prompt
    command_words = {
        # conversation + mode selection
        "new", "開始", "ed", "education", "衛教", "chat", "聊天",
        # edu‑branch commands
        "modify", "修改", "mail", "寄送", "translate", "翻譯", "trans",
    }
    return not session.get("zh_output") and text_lower not in command_words


# ---------------------------------------------------------------------
# Main LINE event handler
# ---------------------------------------------------------------------

def handle_line_message(event):
    """Entry point registered in routes/webhook.py."""

    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    # ── Branch: Gemini needed ─────────────────────────────────────────
    if will_call_gemini(user_input, session):
        try:
            start_time = time.time()
            reply, _   = handle_user_message(user_id, user_input, session)
            elapsed    = time.time() - start_time
            if elapsed > 50:
                raise TimeoutError("⏰ Gemini 回應超時 (>50 秒)")

            # Decide log type
            action_type = "medchat" if session.get("mode") == "chat" else "Gemini reply"
            log_to_sheet(user_id, user_input, reply, session, action_type=action_type, gemini_call="yes")

            # ── MedChat: simple single reply, then return ────────────
            if session.get("mode") == "chat":
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return  # ✅ done

            # ── Education: build multi‑chunk carousel ────────────────
            zh_output        = session.get("zh_output", "")
            translated_output = session.get("translated_output", "")
            zh_chunks        = split_text(f"📄 原文：\n{zh_output}") if zh_output else []
            translated_chunks = split_text(f"🌐 譯文：\n{translated_output}") if translated_output else []

            messages: list[TextSendMessage] = []

            # Take up to 3 content chunks, favouring zh_output first
            content_chunks = zh_chunks[:2]
            remaining      = 3 - len(content_chunks)
            content_chunks.extend(translated_chunks[:remaining])
            messages.extend(TextSendMessage(text=chunk) for chunk in content_chunks)

            # Instruction footer (edu only)
            messages.append(TextSendMessage(
                text=(
                    "📌 您目前可：\n"
                    "1️⃣ 再次輸入: 翻譯/translate/trans 進行翻譯\n"
                    "2️⃣ 輸入: mail/寄送，寄出內容\n"
                    "3️⃣ 輸入 new 重新開始\n"
                    "⚠️ 建議：翻譯或 Gemini 呼叫約需 20 秒，請耐心等候。"
                )
            ))

            # Truncation notice if needed
            if len(zh_chunks) + len(translated_chunks) > 3:
                messages.append(TextSendMessage(
                    text=(
                        "⚠️ 因 LINE 訊息長度限制，部分內容未顯示。\n"
                        "如需完整內容請輸入 mail 或 寄送，以 email 收取全文。"
                    )
                ))

            line_bot_api.reply_message(event.reply_token, messages)

        except TimeoutError as exc:
            log_to_sheet(user_id, user_input, f"❌ TimeoutError: {exc}", session, action_type="Gemini timeout", gemini_call="yes")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ Gemini 回應逾時，請稍後再試或輸入 new 重新開始。"))

        except Exception as exc:
            log_to_sheet(user_id, user_input, f"❌ Unknown Error: {exc}", session, action_type="Exception", gemini_call="yes")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 發生錯誤，請稍後再試或輸入 new 重新開始。"))

        return  # all Gemini paths exit here

    # ── Branch: no Gemini needed (sync reply) ────────────────────────
    reply, _ = handle_user_message(user_id, user_input, session)
    log_to_sheet(user_id, user_input, reply, session, action_type="sync reply", gemini_call="no")
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
