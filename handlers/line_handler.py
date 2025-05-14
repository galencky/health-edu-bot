from linebot.models import TextSendMessage
from linebot import LineBotApi
import os, time

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# Helper to split long text into chunks of max 4000 characters
def split_text(text, chunk_size=4000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# update will_call_gemini()

def will_call_gemini(text: str, session: dict) -> bool:
    text_lower = text.strip().lower()

    # 🚫 Don’t call Gemini until the user has chosen a mode
    if session.get("mode") is None:
        return False

    if session.get("awaiting_modify") or session.get("awaiting_translate_language"):
        return True

    # Treat mode-selection words as commands, not Gemini prompts
    command_words = {
        "new", "開始",
        "ed", "education", "衛教",    # ← added
        "chat", "聊天",              # ← added
        "modify", "修改",
        "mail", "寄送",
        "translate", "翻譯", "trans"
    }

    return not session.get("zh_output") and text_lower not in command_words


def handle_line_message(event):
    user_id = event.source.user_id
    user_input = event.message.text
    session = get_user_session(user_id)

    if will_call_gemini(user_input, session):
        try:
            start = time.time()

            # 1. Handle Gemini logic
            reply, _ = handle_user_message(user_id, user_input, session)

            elapsed = time.time() - start
            if elapsed > 50:
                raise TimeoutError("⏰ Gemini 回應超時 (>50 秒)")

            log_to_sheet(user_id, user_input, reply, session, action_type="Gemini reply", gemini_call="yes")

            # 2. Compose Gemini response messages
            messages = []

            zh_output = session.get("zh_output", "")
            translated_output = session.get("translated_output", "")
            zh_chunks = split_text(f"📄 原文：\n{zh_output}") if zh_output else []
            translated_chunks = split_text(f"🌐 譯文：\n{translated_output}") if translated_output else []

            # Limit total messages to 5: max 3 content, 1 instruction, 1 truncation
            total_message_budget = 5
            instruction_msg = TextSendMessage(text=
                "📌 您目前可：\n"
                "1️⃣ 再次輸入: 翻譯/translate/trans 進行翻譯\n"
                "2️⃣ 輸入: mail/寄送，寄出內容\n"
                "3️⃣ 輸入 new 重新開始\n"
                "⚠️ 請注意: 若進行翻譯需在輸入指令後等待 20 秒左右，請耐心等候回覆..."
            )
            truncation_msg = TextSendMessage(text=
                "⚠️ 因 LINE 訊息長度限制，部分內容未顯示。\n"
                "請輸入 mail 或 寄送，以 email 收到完整內容。"
            )

            # Take up to 3 content chunks, favoring zh_output
            content_chunks = zh_chunks[:2]  # max 2
            remaining_slots = 3 - len(content_chunks)
            content_chunks += translated_chunks[:remaining_slots]

            messages.extend([TextSendMessage(text=chunk) for chunk in content_chunks])
            messages.append(instruction_msg)

            if len(zh_chunks) + len(translated_chunks) > 3:
                messages.append(truncation_msg)

            line_bot_api.reply_message(event.reply_token, messages)

        except TimeoutError as e:
            log_to_sheet(user_id, user_input, f"❌ TimeoutError: {str(e)}", session, action_type="Gemini timeout", gemini_call="yes")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ Gemini 回應逾時，請稍後再試或輸入 new 重新開始。"))
        except Exception as e:
            log_to_sheet(user_id, user_input, f"❌ Unknown Error: {str(e)}", session, action_type="Exception", gemini_call="yes")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="⚠️ 發生錯誤，請稍後再試或輸入 new 重新開始。"))

    else:
        reply, _ = handle_user_message(user_id, user_input, session)
        log_to_sheet(user_id, user_input, reply, session, action_type="sync reply", gemini_call="no")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
