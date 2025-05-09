from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = FastAPI()

# Map of user_id → session dict
sessions = {}

class UserInput(BaseModel):
    message: str

def get_user_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = {
            "original_prompt": None,
            "last_response": None,
            "started": False,
            "awaiting_email": False,
        }
    return sessions[user_id]

def call_gemini(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="""
You are a medical education assistant. Always respond in plain text only.
Do not use markdown formatting such as *, **, or `.
Use:
# Section Title
 - Bullet 1
 - Bullet 2
First respond in English, then in the specified translation language if applicable.
Please retain the translated language used in the prompt unless the user requests a different language.
Do not reference websites.
"""
    )
    response = model.generate_content(prompt, generation_config={"temperature": 0.25})
    return response.text

def handle_user_message(text: str, session: dict) -> tuple[str, bool]:
    text = text.strip()
    text_lower = text.lower()

    # Start new conversation
    if text_lower == "new":
        session["original_prompt"] = None
        session["last_response"] = None
        session["started"] = True
        session["awaiting_email"] = False
        return (
            "🆕 新對話已開始。\n\n請直接輸入您的指令，例如：\n👉 請用日文生成高血壓衛教資訊，強調血壓測量的722法則\n\n📌 系統將自動生成英文版，請選擇非英文語言以獲得翻譯版本。",
            False,
        )

    # Handle email input
    if session.get("awaiting_email"):
        email_pattern = r"[^@]+@[^@]+\.[^@]+"
        if re.fullmatch(email_pattern, text):
            session["awaiting_email"] = False
            return f"✅ 已收到 email：{text}\n目前寄送功能尚在開發中。", False
        else:
            return "⚠️ 請輸入有效的 email 地址，例如 example@gmail.com", False

    # Require "new" first
    if not session["started"]:
        return "❗請輸入 'new' 開始新的衛教對話。", False

    # Start email mailing flow
    if "mail" in text_lower and session["last_response"]:
        session["awaiting_email"] = True
        return "📧 請輸入您要寄送衛教資料的有效 email 地址：", False

    # Modify existing output
    if "modify" in text_lower and session["last_response"] and session["original_prompt"]:
        mod_prompt = (
            f"Please revise the educational material based on the following user instruction:\n\n"
            f"{text}\n\n"
            f"Original prompt:\n{session['original_prompt']}\n\n"
            f"Original response:\n{session['last_response']}"
        )
        session["original_prompt"] = mod_prompt
        session["last_response"] = call_gemini(mod_prompt)
        return session["last_response"], True

    # New prompt: treat as main request
    session["original_prompt"] = text
    session["last_response"] = call_gemini(text)
    return session["last_response"], True

@app.post("/chat")
def chat(input: UserInput):
    user_id = "test-user"
    session = get_user_session(user_id)
    reply, remind = handle_user_message(input.message, session)
    if remind:
        reply += "\n\n📌 若您想將衛教資料寄送 email，請輸入 \"Mail\"，我將會請您輸入有效電子郵件地址。"
    return {"reply": reply}

@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()

    print("🔔 LINE Webhook triggered")
    print("📩 Body:", body.decode("utf-8"))

    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE signature")
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_line_message(event):
    user_id = event.source.user_id
    user_input = event.message.text
    session = get_user_session(user_id)

    print(f"💬 LINE User Input ({user_id}): {user_input}")
    reply, show_reminder = handle_user_message(user_input, session)

    messages = [TextSendMessage(text=reply[:4000])]
    if show_reminder:
        messages.append(TextSendMessage(
            text="📌 若您想將衛教資料寄送 email，請輸入 \"Mail\"，我將會請您輸入有效電子郵件地址。"
        ))

    line_bot_api.reply_message(event.reply_token, messages)

@app.get("/")
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/webhook"]
    }
