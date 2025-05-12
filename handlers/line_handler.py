from linebot.models import TextSendMessage
from linebot import LineBotApi
import os
from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# Split into LINE-safe message chunks
def split_text(text, chunk_size=4000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# Determine whether Gemini will be called
def will_call_gemini(text: str, session: dict) -> bool:
    text_lower = text.strip().lower()

    if not session.get("started"):
        return False

    if session.get("awaiting_modify") or session.get("awaiting_translate_language"):
        return True

    command_words = {"new", "開始", "modify", "修改", "mail", "寄送", "translate", "翻譯", "trans"}
    if not session.get("zh_output") and text_lower not in command_words:
        return True

    return False

def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    # Sync Gemini call + reply
    if will_call_gemini(user_input, session):
        reply, _ = handle_user_message(user_id, user_input, session)
        log_to_sheet(user_id, user_input, reply, session, action_type="Gemini reply", gemini_call="yes")

        messages = []

        if session.get("translated") and session.get("zh_output") and session.get("translated_output"):
            messages.append(TextSendMessage(text=f"📄 原文：\n{session['zh_output']}"))
            messages.append(TextSendMessage(text=f"🌐 譯文：\n{session['translated_output']}"))
            messages.append(TextSendMessage(text=
                "📌 您目前可：\n"
                "1️⃣ 再次輸入: 翻譯/translate/trans 進行翻譯\n"
                "2️⃣ 輸入: mail/寄送，寄出內容\n"
                "3️⃣ 輸入 new 重新開始"
            ))

        elif session.get("zh_output") and not session.get("translated"):
            messages.append(TextSendMessage(text=f"📄 原文：\n{session['zh_output']}"))
            messages.append(TextSendMessage(text=
                "📌 您目前可：\n"
                "1️⃣ 輸入: 修改/modify 調整內容\n"
                "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
                "3️⃣ 輸入: mail/寄送，寄出內容\n"
                "4️⃣ 輸入 new 重新開始"
            ))

        else:
            for chunk in split_text(reply):
                messages.append(TextSendMessage(text=chunk))

        # Limit to 5 messages max per LINE API
        line_bot_api.reply_message(event.reply_token, messages[:5])

    else:
        reply, _ = handle_user_message(user_id, user_input, session)
        log_to_sheet(user_id, user_input, reply, session, action_type="sync reply", gemini_call="no")
        for chunk in split_text(reply):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=chunk))
            break  # Only send 1 reply here to avoid "Reply token already used"
