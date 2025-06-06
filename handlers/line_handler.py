"""
handlers/line_handler.py
────────────────────────
Lightweight LINE adapter.  All conversational logic lives in
handlers.logic_handler.
"""

from __future__ import annotations
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage, FlexSendMessage, AudioSendMessage
from handlers.logic_handler   import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets      import log_to_sheet
from services.gemini_service  import get_references, references_to_flex

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ── helper: split text into LINE-safe chunks (≤4 000 chars) ───────────
def _chunks(txt: str, limit: int = 4000) -> list[str]:
    return [txt[i : i + limit] for i in range(0, len(txt), limit)]

# ── webhook entrypoint (bound in routes/webhook.py) ───────────────────
def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    reply, gemini_called = handle_user_message(user_id, user_input, session)

    bubbles: list = []

    # ──────────────────────────────────────────────────────────────────
    # Chat mode → always single-bubble reply
    # ──────────────────────────────────────────────────────────────────
    if session.get("mode") == "chat":
        # if a TTS was just generated, send audio first
        if session.get("tts_audio_url"):
            bubbles.append(
                AudioSendMessage(
                    original_content_url=session.pop("tts_audio_url"),
                    duration=session.pop("tts_audio_dur", 0)
                )
            )
        bubbles.append(TextSendMessage(text=reply))

    # ──────────────────────────────────────────────────────────────────
    # Education mode
    #   • content bubbles are added ONLY when Gemini just ran
    #   • action-hint bubble is added every turn
    # ──────────────────────────────────────────────────────────────────
    else:
        if gemini_called:                                 # new content this turn
            zh = session.get("zh_output") or ""
            tr = session.get("translated_output") or ""

            zh_chunks = _chunks(f"📄 原文：\n{zh}")[:2] if zh else []
            tr_chunks = _chunks(f"🌐 譯文：\n{tr}")[: max(0, 3-len(zh_chunks))] if tr else []

            for c in (*zh_chunks, *tr_chunks):
                bubbles.append(TextSendMessage(text=c))

            # ── Reference bubble (Flex Message), if references exist ──
            refs = session.get("references") or []
            flex = references_to_flex(refs)
            if flex:
                bubbles.append(FlexSendMessage(alt_text="參考來源", contents=flex))

            if len(zh_chunks) + len(tr_chunks) > 3:
                bubbles.append(TextSendMessage(
                    text="⚠️ 內容過長，僅部分顯示。如需完整內容請輸入 mail / 寄送。"
                ))

        # Tail bubble: action-hint / prompt from logic_handler
        bubbles.append(TextSendMessage(text=reply))

    # ── send to LINE ─────────────────────────────────────────────────
    try:
        line_bot_api.reply_message(event.reply_token, bubbles)
    except Exception as exc:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"⚠️ 發送訊息失敗：{exc}")
        )

    # ── log (MedChat already logs itself) ────────────────────────────
    if session.get("mode") != "chat":
        log_to_sheet(
            user_id,
            user_input,
            reply[:200],
            session,
            action_type="Gemini reply" if gemini_called else "sync reply",
            gemini_call="yes" if gemini_called else "no",
        )
