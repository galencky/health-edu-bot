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
        # Use wait_for for Python 3.9/3.10 compatibility
        async def handle_request():
            body = await request.body()
            body_str = body.decode()
            #print("[WEBHOOK] Raw body:", body_str)
            #print("[WEBHOOK] Signature:", x_line_signature)
            
            # Handle synchronously - FastAPI can manage this
            handler.handle(body_str, x_line_signature)
            return "OK"
        
        return await asyncio.wait_for(handle_request(), timeout=48.0)
    except asyncio.TimeoutError:
        print("[WEBHOOK] Request timed out after 48 seconds")
        # Return OK to LINE to prevent retries, but log the timeout
        return "OK"
    except ValueError as e:
        # Invalid signature - likely not from LINE
        print(f"[WEBHOOK] Invalid signature: {x_line_signature}")
        print(f"[WEBHOOK] ValueError: {e}")
        # Return OK instead of raising to prevent retries
        return "OK"
    except Exception as e:
        # Log full error internally with stack trace
        print(f"[WEBHOOK] Critical error: {type(e).__name__}: {e}")
        print("[WEBHOOK] Stack trace:", traceback.format_exc())
        
        # TODO: In production, send to error tracking service
        # try:
        #     sentry_sdk.capture_exception(e)
        # except:
        #     pass
        
        # Critical: Always return OK to prevent LINE webhook retries
        # But log that we're masking an error
        print("[WEBHOOK] Returning OK to prevent retries, but error occurred!")
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
