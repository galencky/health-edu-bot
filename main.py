from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import google.generativeai as genai

# LINE SDK
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# Load environment
load_dotenv()

# Gemini API setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# LINE credentials
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = FastAPI()

# In-memory session (can be user-specific in future)
session = {
    "language": None,
    "disease": None,
    "topic": None,
    "last_prompt": None,
    "last_response": None,
}

class UserInput(BaseModel):
    message: str

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
        system_instruction="You are a medical education assistant. First respond in English, then translate into the requested language. Do not reference websites."
    )
    response = model.generate_content(prompt)
    return response.text

def handle_user_message(message: str) -> str:
    global session
    text = message.strip().lower()

    if "new" in text:
        session.update({key: None for key in session})
        return "🆕 New chat started."
    elif "modify" in text and session["last_response"]:
        mod_prompt = f"Please revise the following based on this request:\n\n{text}\n\nOriginal:\n{session['last_response']}"
        session["last_prompt"] = mod_prompt
        session["last_response"] = call_gemini(mod_prompt)
        return session["last_response"]
    elif not session["language"]:
        session["language"] = text
        return "🌐 Language set. Please enter disease:"
    elif not session["disease"]:
        session["disease"] = text
        return "🩺 Disease set. Please enter topic:"
    elif not session["topic"]:
        session["topic"] = text
        session["last_prompt"] = build_prompt(session["language"], session["disease"], session["topic"])
        session["last_response"] = call_gemini(session["last_prompt"])
        return session["last_response"]
    else:
        return "✅ Chat complete. Type 'modify' to revise, 'new' to start over."

# Route for curl/Postman-style testing
@app.post("/chat")
def chat(input: UserInput):
    reply = handle_user_message(input.message)
    return {"reply": reply}

# LINE Messaging API webhook
@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()

    # Debug logging (optional — comment out in production)
    print("🔔 LINE Webhook triggered")
    print("📩 Body:", body.decode("utf-8"))

    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE signature")
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_line_message(event):
    user_input = event.message.text
    reply = handle_user_message(user_input)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply[:4000])  # LINE reply limit
    )

@app.get("/")
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/webhook"]
    }
