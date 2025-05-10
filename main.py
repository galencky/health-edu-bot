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
        "endpoints": ["/", "/chat", "/ping", "/webhook"]
    }

@app.get("/ping")
def ping():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
