from __future__ import annotations
import os
import time
from pathlib import Path
from linebot import LineBotApi
from linebot.models import (
    TextSendMessage,
    FlexSendMessage,
    AudioSendMessage,
    MessageEvent,
    TextMessage,
    AudioMessage,
)
from linebot.exceptions import LineBotApiError

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.log_to_sheets import log_to_sheet
from services.gemini_service import references_to_flex, _call_genai
from services.stt_service import transcribe_audio_file
from utils.voicemail_drive import upload_voicemail_to_drive

# -----------------------------------------------
# Custom prompt for voicemail translation
voicemail_prompt = """ You are a medical translation assistant fluent in {lang}. Please translate the following message to {lang}."""
# -----------------------------------------------

# Instantiate LINE client
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def _chunks(txt: str, limit: int = 4000) -> list[str]:
    return [txt[i : i + limit] for i in range(0, len(txt), limit)]


def handle_line_message(event: MessageEvent[TextMessage]):
    """
    1) If session['awaiting_stt_translation'] is True, treat this TextMessage
       as either (a) “no translation (new/無)” or (b) “translate to <lang>”.
       Return immediately after handling.
    2) Otherwise, fall through to the normal handle_user_message(...) logic.
    """
    user_id    = event.source.user_id
    user_input = event.message.text.strip()
    session    = get_user_session(user_id)

    # ───────────────────────────────────────────────────────────────────
    # 1) STT‐translation branch: check this first, before any other logic
    # ───────────────────────────────────────────────────────────────────
    if session.get("awaiting_stt_translation"):
        text_lower = user_input.lower()

        # a) Cancel or “new” path
        if text_lower in {"new", "無"}:
            session.pop("awaiting_stt_translation", None)
            session.pop("stt_transcription", None)

            cancel_reply = "✅ 已取消翻譯。如需重新開始，請輸入 new。"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=cancel_reply)
                )
            except LineBotApiError:
                pass
            return

        # b) Otherwise, treat `user_input` as the target language
        original_text = session.get("stt_transcription", "")
        sys_prompt = voicemail_prompt.format(lang=user_input)

        try:
            # Call Gemini with our custom voicemail_prompt
            translated = _call_genai(original_text, sys_prompt=sys_prompt, temp=0)
            session["stt_last_translation"] = translated          # NEW
            session["mode"] = "chat"                              # keep this line
        except Exception as e:
            # On failure, clear state and inform user
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
        
        # *** HERE: switch into chat mode so TTS works next ***
        session["mode"] = "chat"

        # Build and send the translation reply + TTS hint
        reply_lines = [
            "🌐 翻譯結果：",
            translated,
            "\n若希望將翻譯文句用 AI 語音朗讀，請輸入「朗讀」或是 \"speak\"。"
        ]

        session.pop("awaiting_stt_translation", None)
        session.pop("stt_transcription", None)

        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="\n".join(reply_lines))
            )
        except LineBotApiError:
            pass

        return  # important: stop here and do not fall through

    # ───────────────────────────────────────────────────────────────────
    # 2) Normal bot flow (no STT‐translation in progress)
    # ───────────────────────────────────────────────────────────────────
    reply, gemini_called = handle_user_message(user_id, user_input, session)
    bubbles: list = []

    if session.get("mode") == "chat":
        # If TTS audio is queued, send it first
        if session.get("tts_audio_url"):
            bubbles.append(
                AudioSendMessage(
                    original_content_url=session.pop("tts_audio_url"),
                    duration=session.pop("tts_audio_dur", 0)
                )
            )
        bubbles.append(TextSendMessage(text=reply))
    else:
        if gemini_called:
            zh = session.get("zh_output") or ""
            tr = session.get("translated_output") or ""
            zh_chunks = _chunks(f"📄 原文：\n{zh}")[:2] if zh else []
            tr_chunks = _chunks(f"🌐 譯文：\n{tr}")[: max(0, 3 - len(zh_chunks))] if tr else []
            for c in (*zh_chunks, *tr_chunks):
                bubbles.append(TextSendMessage(text=c))

            refs = session.get("references") or []
            flex = references_to_flex(refs)
            if flex:
                bubbles.append(FlexSendMessage(alt_text="參考來源", contents=flex))

            if len(zh_chunks) + len(tr_chunks) > 3:
                bubbles.append(TextSendMessage(
                    text="⚠️ 內容過長，僅部分顯示。如需完整內容請輸入 mail / 寄送。"
                ))
        bubbles.append(TextSendMessage(text=reply))

    try:
        line_bot_api.reply_message(event.reply_token, bubbles)
    except LineBotApiError as exc:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⚠️ 發送訊息失敗：{exc}")
            )
        except:
            pass

    # Log to Sheets if not in chat‐mode (MedChat logs itself)
    if session.get("mode") != "chat":
        log_to_sheet(
            user_id,
            user_input,
            reply[:200],
            session,
            action_type="Gemini reply" if gemini_called else "sync reply",
            gemini_call="yes" if gemini_called else "no",
        )


def handle_audio_message(event: MessageEvent[AudioMessage]):
    """
    1) Download LINE voicemail → save as ./voicemail/<user>_<ts>.m4a
    2) Upload to Drive (optional link in reply)
    3) Call Gemini STT (upload via Files API, then generate_content)
    4) Store transcription in session, set awaiting_stt_translation=True
    5) Reply with “原始轉錄：<text>\n請輸入欲翻譯之語言；若無，請輸入「無」或「new」。\n(Drive link)”
    """
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

    # 3. Upload to Google Drive
    try:
        drive_link = upload_voicemail_to_drive(str(local_filename), user_id)
    except Exception as e:
        print(f"[Voicemail → Drive] Upload failed: {e}")
        drive_link = None  # continue even if upload fails

    # 4. Call Gemini STT
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

    # 5. Store transcription & set flag, then send prompt
    session["stt_transcription"] = transcription
    session["awaiting_stt_translation"] = True

    reply_lines = [
        "📣 原始轉錄：",
        transcription,
        "",
        "請輸入欲翻譯之語言；若無，請輸入「無」或「new」。"
    ]
    #if drive_link:
    #    reply_lines.extend([
    #        "",
    #        f"🔗 已將語音檔上傳至 Google Drive：",
    #        drive_link
    #    ])

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n".join(reply_lines))
        )
    except LineBotApiError:
        pass

    # (Optional) log to Sheets
    log_to_sheet(
        user_id,
        "[AudioMessage]",
        transcription[:200],
        session,
        action_type="medchat_audio",
        gemini_call="yes",
    )
    return
