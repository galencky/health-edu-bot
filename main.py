<<<<<<< HEAD
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from routes.webhook import webhook_router
from handlers.session_manager import get_user_session

load_dotenv()

app = FastAPI()
app.include_router(webhook_router)

class UserInput(BaseModel):
    message: str

@app.post("/chat")
def chat(input: UserInput):
    from handlers.logic_handler import handle_user_message
    session = get_user_session("test-user")
    reply, _ = handle_user_message(input.message, session)
    return {"reply": reply}

@app.get("/")
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/webhook"]
    }
=======
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
import threading

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from log_to_sheets import log_to_sheet

# ── Environment & Configuration ──────────────────────────────────────────
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET       = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)

app = FastAPI()

# ── Session Storage ───────────────────────────────────────
sessions: dict[str, dict] = {}

class UserInput(BaseModel):
    message: str

def get_user_session(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "started": False,
            "zh_output": None,
            "translated_output": None,
            "translated": False,
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,
        }
    return sessions[user_id]

# ── Gemini Calls ─────────────────────────────────────────────────────────────
def call_zh(prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="""
You are a medical education assistant. Respond in Traditional Chinese, plain text only.
Do not use markdown (*, **, ). Use bullet points and section headers.
"""
    )
    resp = model.generate_content(prompt, generation_config={"temperature": 0.25})
    return resp.text

def call_translate(zh_text: str, target_lang: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=f"""
You are a translation assistant. Translate the following Traditional Chinese text into {target_lang}, plain text only.
Do not alter the meaning. Do not add explanations.
"""
    )
    resp = model.generate_content(zh_text, generation_config={"temperature": 0.25})
    return resp.text

# ── Command Sets ─────────────────────────────────────────────────────────────
new_commands       = {"new", "開始"}
modify_commands    = {"modify", "修改"}
translate_commands = {"translate", "翻譯", "trans"}
mail_commands      = {"mail", "寄送"}

# ── Core Handler ────────────────────────────────────────────────────────────
def handle_user_message(text: str, session: dict) -> tuple[str, bool]:
    raw       = text.strip()
    text_lower = raw.lower()

    if not session["started"]:
        if text_lower in new_commands:
            session.update({
                "started": True,
                "zh_output": None,
                "translated_output": None,
                "translated": False,
                "awaiting_translate_language": False,
                "awaiting_email": False,
                "awaiting_modify": False,
            })
            return (
                "🆕 新對話已開始。\n\n請直接輸入：疾病名稱 + 衛教主題（會產出中文版衛教內容）。",
                False,
            )
        else:
            return (
                "📖 請先讀我: 此聊天室的運作方式:\n\n"
                "Step 1: 輸入疾病與衛教主題（將產出中文版衛教內容）\n"
                "Step 2: 修改中文版內容（輸入「modify」或「修改」）\n"
                "Step 3: 輸入「翻譯」或「translate」或「trans」將其翻譯\n"
                "Step 4: 輸入「mail」或「寄送」寄出中文版與翻譯版\n\n"
                "⚠️ 請先輸入「new」或「開始」以啟動對話。",
                False,
            )

    is_new       = text_lower in new_commands
    is_translate = text_lower in translate_commands
    is_mail      = text_lower in mail_commands
    is_modify_cmd = text_lower in modify_commands

    if sum([is_new, is_translate, is_mail, is_modify_cmd]) > 1:
        return ("⚠️ 同時偵測到多個指令，請一次只執行一項：new/modify/translate/mail。", False)

    if is_new:
        session.update({
            "started": True,
            "zh_output": None,
            "translated_output": None,
            "translated": False,
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,
        })
        return (
            "🆕 已重新開始。\n請輸入：疾病名稱 + 衛教主題。",
            False,
        )

    if session["awaiting_modify"]:
        prompt = (
            f"請根據以下指示修改中文版衛教內容：\n\n{raw}\n\n原始內容：\n{session['zh_output']}"
        )
        new_zh = call_zh(prompt)
        session.update({
            "zh_output": new_zh,
            "awaiting_modify": False
        })
        return (
            f"✅ 已修改中文版內容：\n\n{new_zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "2️⃣ 輸入: mail/寄送，寄出內容\n"
            "3️⃣ 輸入 new 重新開始\n",
            False,
        )

    if is_modify_cmd:
        if session["translated"]:
            return ("⚠️ 已進行翻譯，現階段僅可再翻譯或寄送。如需重新調整，請輸入 new 重新開始。", False)
        if not session["zh_output"]:
            return ("⚠️ 尚未產出中文版內容，無法修改，請先輸入疾病與主題。", False)
        session["awaiting_modify"] = True
        return ("✏️ 請輸入您的修改指示，例如：強調飲食控制。", False)

    if is_translate:
        if not session["zh_output"]:
            return ("⚠️ 尚未產出中文版內容，請先輸入疾病與主題。", False)
        session["awaiting_translate_language"] = True
        return ("🌐 請輸入您要翻譯成的語言，例如：日文、泰文…", False)

    if session["awaiting_translate_language"]:
        target_lang = raw
        zh_text     = session["zh_output"]
        translated  = call_translate(zh_text, target_lang)
        session.update({
            "translated_output": translated,
            "translated": True,
            "awaiting_translate_language": False,
        })
        return (
            f"🌐 翻譯完成（目標語言：{target_lang}）：\n\n"
            f"原文：\n{zh_text}\n\n"
            f"譯文：\n{translated}\n\n"
            "您目前可：\n"
            "1️⃣ 再次輸入: 翻譯/translate/trans 進行翻譯\n"
            "2️⃣ 輸入: mail/寄送，寄出內容\n"
            "3️⃣ 輸入 new 重新開始\n",
            False,
        )

    if is_mail:
        if not session["zh_output"]:
            return ("⚠️ 尚無內容可寄送，請先輸入疾病與主題。", False)
        session["awaiting_email"] = True
        return ("📧 請輸入您要寄送至的 email 地址：", False)

    if session["awaiting_email"]:
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        if re.fullmatch(email_pattern, raw):
            session["awaiting_email"] = False
            return (
                f"✅ 已收到 email：{raw}\n目前寄送功能尚在開發中。", 
                False,
            )
        else:
            return ("⚠️ 無效 email，請重新輸入，例如：example@gmail.com", False)

    if not session["zh_output"]:
        zh = call_zh(raw)
        session["zh_output"] = zh
        return (
            f"✅ 中文版衛教內容已生成：\n\n{zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 修改/modify 調整內容\n"
            "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "3️⃣ 輸入: mail/寄送，寄出內容\n"
            "4️⃣ 輸入 new 重新開始\n",
            False,
        )

    return (
        "⚠️ 指令不明，請依照下列操作：\n"
        "• new/開始 → 重新開始\n"
        "• modify/修改 → 進入修改模式\n"
        "• translate/翻譯/trans → 進行翻譯\n"
        "• mail/寄送 → 寄出內容\n",
        False,
    )

# ── FastAPI Routes ──────────────────────────────────────────────────────────
@app.post("/chat")
def chat(input: UserInput):
    user_id = "test-user"
    session = get_user_session(user_id)
    reply, _ = handle_user_message(input.message, session)
    return {"reply": reply}

@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode(), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(400, "Invalid LINE signature")
    return "OK"

# ── LINE Event Handler ──────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessage)
def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    def will_call_gemini(text: str, session: dict) -> bool:
        text_lower = text.strip().lower()
        if not session["started"]:
            return False
        if session["awaiting_modify"]:
            return True
        if session["awaiting_translate_language"]:
            return True
        if not session["zh_output"]:
            return True
        return False

    if will_call_gemini(user_input, session):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⏳ 已將您的指令用 API 傳至 Gemini，請等待回覆（通常需 10-20 秒）...")
        )
        def process_and_push_reply():
            reply, _ = handle_user_message(user_input, session)
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=reply[:4000])
            )
            log_to_sheet(user_id, user_input, reply, session, action_type="Gemini reply", gemini_call="yes")
        threading.Thread(target=process_and_push_reply).start()
    else:
        reply, _ = handle_user_message(user_input, session)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply[:4000])
        )
        log_to_sheet(user_id, user_input, reply, session, action_type="sync reply", gemini_call="no")


@app.get("/")
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/webhook"]
    }
>>>>>>> 1cbc8910ba21437104a0d6bb00fd2307aaec7c72
