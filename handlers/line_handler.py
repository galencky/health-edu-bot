"""Reply handler for LINE webhook events.

• Distinguishes between education and MedChat modes.
• Calls Gemini only when needed (after mode chosen).
• Builds carousel replies only for the education branch.
"""

import os
import time
from linebot import LineBotApi
from linebot.models import TextSendMessage

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ── helpers ──────────────────────────────────────────────────────────
def split_text(text: str, chunk_size: int = 4000) -> list[str]:
    """Split long text into LINE-safe ≤4000-char chunks."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def will_call_gemini(text: str, session: dict) -> bool:
    """Return True when this message should trigger a Gemini call."""
    text_lower = text.strip().lower()

    # 1) Gemini never runs until user picks a mode
    if session.get("mode") is None:
        return False

    # 2) Pending edu operations always call Gemini
    if session.get("awaiting_modify") or session.get("awaiting_translate_language"):
        return True

    # 3) Fresh prompts that need zh_output
    command_words = {
        "new", "開始",
        "ed", "education", "衛教",
        "chat", "聊天",
        "modify", "修改",
        "mail", "寄送",
        "translate", "翻譯", "trans",
    }
    return not session.get("zh_output") and text_lower not in command_words


# ── main LINE event handler ──────────────────────────────────────────
def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    # ── Branch A: needs Gemini ───────────────────────────────────────
    if will_call_gemini(user_input, session):
        try:
            start = time.time()
            reply, _ = handle_user_message(user_id, user_input, session)
            if time.time() - start > 50:
                raise TimeoutError("⏰ Gemini 回應超時 (>50 秒)")

            # Log once *unless* MedChat already logged inside handler
            if session.get("mode") != "chat":
                log_to_sheet(user_id, user_input, reply, session,
                             action_type="Gemini reply", gemini_call="yes")

            # ── MedChat: single-text reply then exit
            if session.get("mode") == "chat":
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return  # ✅ MedChat done

            # ── Education: assemble carousel reply
            zh_out = session.get("zh_output", "")
            tr_out = session.get("translated_output", "")
            zh_chunks = split_text(f"📄 原文：\n{zh_out}") if zh_out else []
            tr_chunks = split_text(f"🌐 譯文：\n{tr_out}") if tr_out else []

            msgs: list[TextSendMessage] = []
            content = zh_chunks[:2] + tr_chunks[: max(0, 3 - len(zh_chunks[:2]))]
            msgs.extend(TextSendMessage(text=c) for c in content)

            msgs.append(TextSendMessage(
                text=("📌 您目前可：\n"
                      "1️⃣ 再次輸入: 翻譯/translate/trans\n"
                      "2️⃣ 輸入: mail/寄送\n"
                      "3️⃣ 輸入 new 重新開始\n"
                      "⚠️ Gemini 呼叫約需 20 秒，請耐心等候")
            ))
            if len(zh_chunks) + len(tr_chunks) > 3:
                msgs.append(TextSendMessage(
                    text=("⚠️ 部分內容因長度受限未顯示。\n"
                          "如需完整內容請輸入 mail 或 寄送，以 email 收取全文。")
                ))

            line_bot_api.reply_message(event.reply_token, msgs)

        except TimeoutError:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ Gemini 回應逾時，請稍後再試或輸入 new 重新開始。"))
        except Exception as exc:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"⚠️ 發生錯誤: {exc}。請稍後再試或輸入 new 重新開始。"))
        return

    # ── Branch B: synchronous reply (no Gemini) ──────────────────────
    reply, _ = handle_user_message(user_id, user_input, session)
    log_to_sheet(user_id, user_input, reply, session,
                 action_type="sync reply", gemini_call="no")
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
