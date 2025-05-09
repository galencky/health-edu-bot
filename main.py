from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ── Environment & Configuration ─────────────────────────────────────────────
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET       = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)

app = FastAPI()

# ── Session Storage ──────────────────────────────────────────────────────────
# In-memory; for production consider Redis
sessions: dict[str, dict] = {}

class UserInput(BaseModel):
    message: str

def get_user_session(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "started": False,
            "zh_output": None,                 # last generated 中文版內容
            "translated_output": None,         # last translated 內容
            "translated": False,               # whether translation has occurred
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,          # waiting for modify instructions
        }
    return sessions[user_id]

# ── Gemini Calls ─────────────────────────────────────────────────────────────
def call_zh(prompt: str) -> str:
    """Generate zh-TW content at temperature=0.25."""
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="""
You are a medical education assistant. Respond in Traditional Chinese, plain text only.
Do not use markdown (*, **, `). Use bullet points and section headers.
"""
    )
    resp = model.generate_content(prompt, generation_config={"temperature": 0.25})
    return resp.text

def call_translate(zh_text: str, target_lang: str) -> str:
    """Translate zh-TW text into target_lang at temperature=0.25."""
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
    """
    Returns (reply_text, needs_reminder_footer)
    """
    raw        = text.strip()
    text_lower = raw.lower()

    # 1) Pre-start: require "new"/"開始"
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
                "🆕 新對話已開始。\n\n"
                "請直接輸入：疾病名稱 + 衛教主題（會產出中文版衛教內容）。",
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

    # 2) Mutual‐exclusion: detect primary commands
    is_new        = text_lower in new_commands
    is_translate  = text_lower in translate_commands
    is_mail       = text_lower in mail_commands
    is_modify_cmd = text_lower in modify_commands

    # If more than one primary command in one input → reject
    if sum([is_new, is_translate, is_mail, is_modify_cmd]) > 1:
        return ("⚠️ 同時偵測到多個指令，請一次只執行一項：new/modify/translate/mail。", False)

    # 3) Handle "new" anytime
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

    # 4) Awaiting modify instructions?
    if session["awaiting_modify"]:
        prompt = (
            f"請根據以下指示修改中文版衛教內容：\n\n"
            f"{raw}\n\n"
            f"原始內容：\n{session['zh_output']}"
        )
        # notify user then call Gemini
        new_zh = call_zh(prompt)
        session.update({
            "zh_output": new_zh,
            "awaiting_modify": False
        })
        return (
            "已將您的指令用api傳至Gemini，請稍等回覆(通常需10-20秒)。\n\n"
            f"✅ 已修改中文版內容：\n\n{new_zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "2️⃣ 輸入: mail/寄送，寄出內容\n"
            "3️⃣ 輸入 new 重新開始\n",
            False,
        )

    # 5) Handle "modify" command
    if is_modify_cmd:
        if session["translated"]:
            return ("⚠️ 已進行翻譯，現階段僅可再翻譯或寄送。如需重新調整，請輸入 new 重新開始。", False)
        if not session["zh_output"]:
            return ("⚠️ 尚未產出中文版內容，無法修改，請先輸入疾病與主題。", False)
        session["awaiting_modify"] = True
        return ("✏️ 請輸入您的修改指示，例如：強調飲食控制。", False)

    # 6) Awaiting translate‐to language?
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
            "已將您的指令用api傳至Gemini，請稍等回覆(通常需10-20秒)。\n\n"
            f"🌐 翻譯完成（目標語言：{target_lang}）：\n\n"
            f"原文：\n{zh_text}\n\n"
            f"譯文：\n{translated}\n\n"
            "您目前可：\n"
            "1️⃣ 再次輸入: 翻譯/translate/trans 進行再翻譯\n"
            "2️⃣ 輸入: mail/寄送，寄出內容\n",
            False,
        )

    # 7) Handle "translate" command
    if is_translate:
        if not session["zh_output"]:
            return ("⚠️ 尚未產出中文版內容，請先輸入疾病與主題。", False)
        if session["translated"]:
            return ("⚠️ 已完成翻譯，僅可再翻譯或寄送，或輸入 new 重新開始。", False)
        session["awaiting_translate_language"] = True
        return ("🌐 請輸入您要翻譯成的語言，例如：日文、泰文…", False)

    # 8) Handle "mail" command
    if is_mail:
        if not session["zh_output"]:
            return ("⚠️ 尚無內容可寄送，請先輸入疾病與主題。", False)
        session["awaiting_email"] = True
        return ("📧 請輸入您要寄送至的 email 地址：", False)

    # 9) Handle email input
    if session["awaiting_email"]:
        email_pattern = r"^[^@]+@[^@]+\.[^@]+$"
        if re.fullmatch(email_pattern, raw):
            session["awaiting_email"] = False
            return (
                f"✅ 已收到 email：{raw}\n"
                "目前寄送功能尚在開發中。", 
                False,
            )
        else:
            return ("⚠️ 無效 email，請重新輸入，例如：example@gmail.com", False)

    # 10) Main zh-TW generation (only when no zh_output yet)
    if not session["zh_output"]:
        zh = call_zh(raw)
        session["zh_output"] = zh
        return (
            "已將您的指令用api傳至Gemini，請稍等回覆(通常需10-20秒)。\n\n"
            f"✅ 中文版衛教內容已生成：\n\n{zh}\n\n"
            "📌 您目前可：\n"
            "1️⃣ 輸入: 修改/modify 調整內容\n"
            "2️⃣ 輸入: 翻譯/translate/trans 進行翻譯\n"
            "3️⃣ 輸入: mail/寄送，寄出內容\n"
            "4️⃣ 輸入 new 重新開始\n",
            False,
        )

    # 11) Fallback for invalid commands
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
    # NOTE: for real multi-user, don't hardcode test-user
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

@handler.add(MessageEvent, message=TextMessage)
def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    reply, _ = handle_user_message(user_input, session)
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text=reply[:4000])]
    )

@app.get("/")
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/webhook"]
    }
