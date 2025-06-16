# === File: routes/webhook.py ===

from fastapi import APIRouter, Request, Header, HTTPException
from linebot.models import MessageEvent, TextMessage, AudioMessage  # <-- import AudioMessage
from handlers.line_handler import handle_line_message, handle_audio_message  # <-- import new handler
from linebot import WebhookHandler
import os
import asyncio
import traceback

webhook_router = APIRouter()
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@webhook_router.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    # Add timeout protection to prevent hanging webhooks
    try:
        async with asyncio.timeout(25.0):  # 25 second timeout (LINE has 30s limit)
            body = await request.body()
            body_str = body.decode()
            #print("[WEBHOOK] Raw body:", body_str)
            #print("[WEBHOOK] Signature:", x_line_signature)
            
            # Handle synchronously - FastAPI can manage this
            handler.handle(body_str, x_line_signature)
            return "OK"
    except asyncio.TimeoutError:
        print("[WEBHOOK] Request timed out after 25 seconds")
        # Return OK to LINE to prevent retries, but log the timeout
        return "OK"
    except ValueError as e:
        # Invalid signature - likely not from LINE
        print(f"[WEBHOOK] Invalid signature: {x_line_signature}")
        # Return OK instead of raising to prevent retries
        return "OK"
    except Exception as e:
        # Log full error internally but return OK to prevent retries
        print("[WEBHOOK] Exception:", traceback.format_exc())
        # Critical: Always return OK to prevent LINE webhook retries
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
