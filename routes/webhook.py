from fastapi import APIRouter, Request, Header, HTTPException
from linebot.models import MessageEvent, TextMessage
from handlers.line_handler import handle_line_message
from linebot import WebhookHandler
import os
import traceback

webhook_router = APIRouter()
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@webhook_router.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        #print("[WEBHOOK] Raw body:", body)
        #print("[WEBHOOK] Signature:", x_line_signature)
        handler.handle(body.decode(), x_line_signature)
    except Exception as e:
        #print("[WEBHOOK ERROR]", e)
        #print(traceback.format_exc())
        raise HTTPException(400, str(e))
    return "OK"

# Register text message handler
handler.add(MessageEvent, message=TextMessage)(handle_line_message)

# Optionally, handle other message/event types to prevent 400 on stickers, images, etc
from linebot.models import MessageEvent, StickerMessage, ImageMessage

def fallback_handler(event):
    print("[WEBHOOK] Unhandled event type:", type(event), event)
    # Optionally reply or just ignore
    return

handler.add(MessageEvent, message=StickerMessage)(fallback_handler)
handler.add(MessageEvent, message=ImageMessage)(fallback_handler)
# You can add more as needed, or handle all unknowns with a generic handler.
