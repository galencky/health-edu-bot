from fastapi import APIRouter, Request, Header, HTTPException
from linebot.models import MessageEvent, TextMessage
from handlers.line_handler import handle_line_message
from linebot import WebhookHandler
import os

webhook_router = APIRouter()
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@webhook_router.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode(), x_line_signature)
    except Exception as e:
        raise HTTPException(400, str(e))
    return "OK"

handler.add(MessageEvent, message=TextMessage)(handle_line_message)
