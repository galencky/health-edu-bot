"""
handlers/line_handler.py
────────────────────────
Lightweight LINE adapter.  All conversational logic lives in
handlers.logic_handler.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from linebot import LineBotApi
from linebot.models import TextSendMessage, FlexSendMessage, AudioSendMessage, MessageEvent, TextMessage, AudioMessage
from linebot.exceptions import LineBotApiError

from handlers.logic_handler   import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets      import log_to_sheet
from services.gemini_service  import get_references, references_to_flex, call_translate
from services.stt_service import transcribe_audio_file
from utils.voicemail_drive import upload_voicemail_to_drive

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ── helper: split text into LINE-safe chunks (≤4 000 chars) ───────────
def _chunks(txt: str, limit: int = 4000) -> list[str]:
    return [txt[i : i + limit] for i in range(0, len(txt), limit)]

# ── webhook entrypoint (bound in routes/webhook.py) ───────────────────
def handle_line_message(event):
    user_id    = event.source.user_id
    user_input = event.message.text
    session    = get_user_session(user_id)

    # ───────────────────────────────────────────────────────────────────
    # 1) If we’re waiting for STT‐translation choice, intercept here
    # ───────────────────────────────────────────────────────────────────
    if session.get("awaiting_stt_translation"):
        text_lower = user_input.lower()
        # If user cancels or starts over:
        if text_lower in {"new", "無"}:
            session.pop("awaiting_stt_translation", None)
            session.pop("stt_transcription", None)
            reply = "✅ 已取消翻譯。如需重新開始，請輸入 new。"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply)
                )
            except LineBotApiError:
                pass
            return

        # Otherwise, treat `user_input` as the target language for translation:
        original_text = session.get("stt_transcription", "")
        try:
            translated = call_translate(original_text, user_input)
        except Exception as e:
            # If translation fails, inform user and clear flags
            session.pop("awaiting_stt_translation", None)
            session.pop("stt_transcription", None)
            err_reply = f"⚠️ 翻譯失敗：{e}"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=err_reply)
                )
            except LineBotApiError:
                pass
            return

        # Build the reply: show 翻譯結果, plus prompt for TTS if desired
        reply_lines = []
        reply_lines.append("🌐 **翻譯結果**：")
        reply_lines.append(translated)
        reply_lines.append("\n若希望將翻譯文句用 AI 語音朗讀，請輸入「朗讀」或是 \"speak\"。")

        # Clear STT‐translation state
        session.pop("awaiting_stt_translation", None)
        session.pop("stt_transcription", None)

        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="\n".join(reply_lines))
            )
        except LineBotApiError:
            pass
        return

    # ───────────────────────────────────────────────────────────────────
    # 2) Otherwise, proceed with normal “user text → logic_handler”
    # ───────────────────────────────────────────────────────────────────

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

# ── handle an incoming AudioMessage (voicemail) ───────────────────────
def handle_audio_message(event: MessageEvent[AudioMessage]):
    user_id     = event.source.user_id
    message_id  = event.message.id
    session     = get_user_session(user_id)

    # 1. Download the raw audio from LINE
    try:
        message_content = line_bot_api.get_message_content(message_id)
    except LineBotApiError:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 無法下載語音檔，請稍後重試。")
        )
        return

    # 2. Save locally under ./voicemail/
    save_dir = Path("voicemail")
    save_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    local_filename = save_dir / f"{user_id}_{timestamp}.m4a"

    try:
        with open(local_filename, "wb") as f:
            for chunk in message_content.iter_content():
                f.write(chunk)
    except Exception:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 儲存語音檔失敗，請稍後重試。")
        )
        return

    # 3. Upload the voicemail to Google Drive
    try:
        drive_link = upload_voicemail_to_drive(str(local_filename), user_id)
    except Exception as e:
        # If Drive upload fails, log and continue
        print(f"[Voicemail → Drive] 上傳失敗：{e}")
        drive_link = None

    # 4. Call Gemini STT (upload + transcript)
    try:
        transcription = transcribe_audio_file(str(local_filename))
    except Exception as e:
        print(f"[STT ERROR] {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 語音轉文字失敗，請稍後重試。")
        )
        return

    if not transcription:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 轉錄內容為空，無法處理。")
        )
        return

    # 5. Instead of translating immediately, prompt user to choose translation
    session["awaiting_stt_translation"] = True
    session["stt_transcription"] = transcription

    # Build prompt back to user
    reply_lines = []
    reply_lines.append("📣 **原始轉錄**：")
    reply_lines.append(transcription)
    reply_lines.append("\n請輸入欲翻譯之語言；若無，請輸入「無」或「new」。")

    if drive_link:
        #reply_lines.append(f"\n🔗 已將語音檔上傳至 Google Drive：\n{drive_link}")

        final_reply = "\n".join(reply_lines)

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=final_reply)
        )
    except LineBotApiError:
        pass

    # (Optional) log to Sheets if desired
    log_to_sheet(
        user_id,
        "[AudioMessage]",
        transcription[:200],
        session,
        action_type="medchat_audio",
        gemini_call="yes",
    )
    return
