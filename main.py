from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import google.generativeai as genai

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
            "language": None,
            "disease": None,
            "topic": None,
            "last_prompt": None,
            "last_response": None,
            "started": False,
        }
    return sessions[user_id]

def build_prompt(language, disease, topic):
    return (
        f"Please create a short, clear patient education pamphlet in two parts:\n\n"
        f"1. English version\n"
        f"2. Translated version in {language}\n\n"
        f"Topic: {disease} — {topic}\n\n"
        f"The goal is to help clinicians educate patients or caregivers in their native language during a clinic visit."
    )

def call_gemini(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="""
You are a medical education assistant. Always respond in plain text only.

Do not use markdown formatting such as *, **, `, or numbered lists like 1., 2., etc.

Use plain headings and dashes for structure:

# Section Title
 - Bullet point 1
 - Bullet point 2

First respond in clear English.
Then repeat the same in the requested translation language.
Do not reference any websites.
"""
    )
    response = model.generate_content(prompt)
    return response.text

def handle_user_message(text: str, session: dict) -> tuple[str, bool]:
    text = text.strip()
    text_lower = text.lower()

    # Require new to start
    if not session["started"]:
        if text_lower == "new":
            for k in session: session[k] = None
            session["started"] = True
            return (
                "🆕 已開始新的對話。\n\n請輸入您希望翻譯的語言（例如：泰文、越南文），最終內容會以英文和該語言雙語呈現。",
                False,
            )
        else:
            return "❗請輸入 'new' 開始新的衛教對話。", False

    if "mail" in text_lower:
        return "📧 mail 功能即將推出。", False

    if "modify" in text_lower and session["last_response"]:
        mod_prompt = f"Please revise the following based on this request:\n\n{text}\n\nOriginal:\n{session['last_response']}"
        session["last_prompt"] = mod_prompt
        session["last_response"] = call_gemini(mod_prompt)
        return session["last_response"], True

    if not session["language"]:
        session["language"] = text
        return "🌐 已設定語言。請輸入疾病名稱：", False
    elif not session["disease"]:
        session["disease"] = text
        return "🩺 已設定疾病。請輸入您想要的衛教主題：", False
    elif not session["topic"]:
        session["topic"] = text
        session["last_prompt"] = build_prompt(session["language"], session["disease"], session["topic"])
        session["last_response"] = call_gemini(session["last_prompt"])
        return session["last_response"], True
    else:
        mod_prompt = f"請根據以下需求修改原始內容：\n\n{text}\n\n原始內容：\n{session['last_response']}"
        session["last_prompt"] = mod_prompt
        session["last_response"] = call_gemini(mod_prompt)
        return session["last_response"], True

@app.post("/chat")
def chat(input: UserInput):
    # Debug-only test with mock user ID
    user_id = "test-user"
    session = get_user_session(user_id)
    print("🧪 /chat triggered")
    print("🔹 User input:", input.message)
    reply, remind = handle_user_message(input.message, session)
    if remind:
        reply += "\n\n📌 衛教文章生成完畢，請輸入任何指令進行修改，\n若要生成新的衛教文章，請輸入\"New\"，\n如果要寄 email，請輸入\"Mail\"後輸入有效電子郵件。"
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
            text="📌 衛教文章生成完畢，請輸入任何指令進行修改，\n若要生成新的衛教文章，請輸入\"New\"，\n如果要寄 email，請輸入\"Mail\"後輸入有效電子郵件。"
        ))

    line_bot_api.reply_message(event.reply_token, messages)

@app.get("/")
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/webhook"]
    }
