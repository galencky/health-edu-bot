# === File: routes/webhook.py ===

from fastapi import APIRouter, Request, Header, HTTPException
from linebot.models import MessageEvent, TextMessage, AudioMessage  # <-- import AudioMessage
from handlers.line_handler import handle_line_message, handle_audio_message  # <-- import new handler
from linebot import WebhookHandler
import os
import traceback

webhook_router = APIRouter()
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@webhook_router.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        body_str = body.decode()
        #print("[WEBHOOK] Raw body:", body_str)
        #print("[WEBHOOK] Signature:", x_line_signature)
        handler.handle(body_str, x_line_signature)
    except ValueError as e:
        # Invalid signature - likely not from LINE
        print(f"[WEBHOOK] Invalid signature: {x_line_signature}")
        raise HTTPException(400, "Invalid signature")
    except Exception as e:
        # Log full error internally but return generic message
        print("[WEBHOOK] Exception:", traceback.format_exc())
        raise HTTPException(400, "Bad request")
    return "OK"

# Register text message handler
handler.add(MessageEvent, message=TextMessage)(handle_line_message)

# **New**: register audio message handler (voicemail)
handler.add(MessageEvent, message=AudioMessage)(handle_audio_message)

# Existing fallback handlers for stickers/images...
from linebot.models import StickerMessage, ImageMessage
def fallback_handler(event):
    print("[WEBHOOK] Unhandled event type:", type(event), event)
    return

handler.add(MessageEvent, message=StickerMessage)(fallback_handler)
handler.add(MessageEvent, message=ImageMessage)(fallback_handler)
