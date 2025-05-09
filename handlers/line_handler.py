from linebot.models import TextSendMessage
from linebot import LineBotApi
import os
import threading
from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    def will_call_gemini(text: str, session: dict) -> bool:
        text_lower = text.strip().lower()
        return not session["started"] or session["awaiting_modify"] or \
               session["awaiting_translate_language"] or not session["zh_output"]

    if will_call_gemini(user_input, session):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⏳ 已將您的指令用 API 傳至 Gemini，請等待回覆（通常需 10-20 秒）...")
        )
        def process():
            reply, _ = handle_user_message(user_input, session)
            line_bot_api.push_message(user_id, TextSendMessage(text=reply[:4000]))
            log_to_sheet(user_id, user_input, reply, session, action_type="Gemini reply", gemini_call="yes")
        threading.Thread(target=process).start()
    else:
        reply, _ = handle_user_message(user_input, session)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply[:4000]))
        log_to_sheet(user_id, user_input, reply, session, action_type="sync reply", gemini_call="no")