from __future__ import annotations
import os
import time
import asyncio
from pathlib import Path
from linebot import LineBotApi
from linebot.models import (
    TextSendMessage,
    FlexSendMessage,
    AudioSendMessage,
    MessageEvent,
    TextMessage,
    AudioMessage,
    QuickReply,
)
from linebot.exceptions import LineBotApiError

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.logging import log_chat, upload_voicemail
from utils.google_drive_service import upload_stt_translation_log
from services.gemini_service import references_to_flex, _call_genai
from services.stt_service import transcribe_audio_file
from utils.paths import VOICEMAIL_DIR
from utils.command_sets import new_commands, create_quick_reply_items, VOICE_TRANSLATION_OPTIONS, TTS_OPTIONS, COMMON_LANGUAGES
from utils.retry_utils import exponential_backoff, RetryError
from utils.validators import sanitize_user_id, sanitize_filename, create_safe_path

# -----------------------------------------------
# Custom prompt for voicemail translation
voicemail_prompt = """ You are a medical translation assistant fluent in {lang}. Please translate the following message to {lang}."""
# -----------------------------------------------

# BUG FIX: Added file size limits to prevent disk exhaustion attacks
MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for audio files

# Concurrency limits to prevent resource exhaustion
import threading
_active_audio_processing = 0
_audio_lock = threading.Lock()
MAX_CONCURRENT_AUDIO = 3

# Instantiate LINE client
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def _chunks(txt: str, limit: int = 4000) -> list[str]:
    return [txt[i : i + limit] for i in range(0, len(txt), limit)]

def _send_error_reply(event, message: str):
    """Helper to send error reply with safe fallback"""
    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
    except LineBotApiError:
        pass


def handle_line_message(event: MessageEvent[TextMessage]):
    """
    Handle LINE text messages with error recovery.
    
    1) If session['awaiting_stt_translation'] is True, treat this TextMessage
       as either (a) "no translation (new/無)" or (b) "translate to <lang>".
       Return immediately after handling.
    2) Otherwise, fall through to the normal handle_user_message(...) logic.
    """
    try:
        user_id    = event.source.user_id
        user_input = event.message.text.strip()
        session    = get_user_session(user_id)

        # ------------------------------------------------------------------
        # Always flush any queued TTS audio FIRST (works in edu *and* chat)
        # ------------------------------------------------------------------
        bubbles: list = []
        if session.get("tts_audio_url"):
            bubbles.append(
                AudioSendMessage(
                    original_content_url=session.pop("tts_audio_url"),
                    duration=session.pop("tts_audio_dur", 0)
                )
            )

        # ───────────────────────────────────────────────────────────────────
        # 1) STT‐translation branch: check this first, before any other logic
        # ───────────────────────────────────────────────────────────────────
        if session.get("awaiting_stt_translation"):
            text_lower = user_input.lower()

            # a) Cancel or "new" path
            if text_lower == "new":
            session.pop("awaiting_stt_translation", None)
            session.pop("stt_transcription", None)

            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="✅ 已取消翻譯",
                        quick_reply=QuickReply(items=create_quick_reply_items(["new"]))
                    )
                )
            except LineBotApiError:
                pass
            return
        
        # b) "translate_voice" - prompt for language selection
        if text_lower == "translate_voice":
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="🌐 請選擇翻譯語言：",
                        quick_reply=QuickReply(items=create_quick_reply_items(COMMON_LANGUAGES))
                    )
                )
            except LineBotApiError:
                pass
            return

        # c) Otherwise, treat `user_input` as the target language
        original_text = session.get("stt_transcription", "")
        sys_prompt = voicemail_prompt.format(lang=user_input)

        try:
            # Call Gemini with our custom voicemail_prompt
            translated = _call_genai(original_text, sys_prompt=sys_prompt, temp=0)
            session["stt_last_translation"] = translated          # NEW
            session["mode"] = "chat"                              # keep this line
            
            # Upload text file to Google Drive for STT translation
            try:
                drive_link, _ = upload_stt_translation_log(user_id, original_text, translated, user_input)
                if drive_link:
                    print(f"✅ [STT] Uploaded translation text to Drive: {drive_link}")
            except Exception as upload_error:
                print(f"⚠️ [STT] Failed to upload translation: {upload_error}")
                # Don't fail the translation if logging fails
            
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
        session["started"] = True   

        # Build and send the translation reply
        reply_lines = [
            "🌐 翻譯結果：",
            translated
        ]

        session.pop("awaiting_stt_translation", None)
        session.pop("stt_transcription", None)
        session.pop("stt_audio_filename", None)  # Clean up filename too

        # Add quick reply for TTS
        quick_reply = QuickReply(items=create_quick_reply_items(TTS_OPTIONS))
        
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="\n".join(reply_lines), quick_reply=quick_reply)
            )
        except LineBotApiError:
            pass
        
        # Log the translation action
        log_chat(
            user_id,
            f"[STT Translation Request] {user_input}",
            translated[:200],
            session,
            action_type="translate",
            gemini_call="yes"
        )

        return  # important: stop here and do not fall through

    # ───────────────────────────────────────────────────────────────────
    # 2) Normal bot flow (no STT‐translation in progress)
    # ───────────────────────────────────────────────────────────────────
    reply, gemini_called, quick_reply_data = handle_user_message(user_id, user_input, session)

    if session.get("mode") == "chat":
        # If TTS audio is queued, send it first
        if session.get("tts_audio_url"):
            bubbles.append(
                AudioSendMessage(
                    original_content_url=session.pop("tts_audio_url"),
                    duration=session.pop("tts_audio_dur", 0)
                )
            )
        # Add quick reply if available
        if quick_reply_data:
            bubbles.append(TextSendMessage(
                text=reply,
                quick_reply=QuickReply(items=quick_reply_data["items"])
            ))
        else:
            bubbles.append(TextSendMessage(text=reply))
    else:
        # Only show content when it's newly generated/modified (gemini_called=True)
        if gemini_called:
            zh = session.get("zh_output") or ""
            tr = session.get("translated_output") or ""
            
            if zh or tr:
                zh_chunks = _chunks(f"📄 原文：\n{zh}")[:2] if zh else []
                tr_chunks = _chunks(f"🌐 譯文：\n{tr}")[: max(0, 3 - len(zh_chunks))] if tr else []
                for c in (*zh_chunks, *tr_chunks):
                    bubbles.append(TextSendMessage(text=c))

                # BUG FIX: Show references when content is displayed
                refs = session.get("references") or []
                flex = references_to_flex(refs)
                if flex:
                    bubbles.append(FlexSendMessage(alt_text="參考來源", contents=flex))

                if len(zh_chunks) + len(tr_chunks) > 3:
                    bubbles.append(TextSendMessage(
                        text="⚠️ 內容過長，僅部分顯示。如需完整內容請點擊下方按鈕：",
                        quick_reply=QuickReply(items=create_quick_reply_items([("📧 寄送", "mail")]))
                    ))
        
        # Add quick reply if available
        if quick_reply_data:
            bubbles.append(TextSendMessage(
                text=reply,
                quick_reply=QuickReply(items=quick_reply_data["items"])
            ))
        else:
            bubbles.append(TextSendMessage(text=reply))

    try:
        line_bot_api.reply_message(event.reply_token, bubbles)
    except LineBotApiError as exc:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⚠️ 發送訊息失敗：{exc}")
            )
        except Exception as e:
            print(f"[LINE] Failed to send error message: {e}")

    # Log if not in chat‐mode (MedChat logs itself)
    if session.get("mode") != "chat":
        log_chat(
            user_id,
            user_input,
            reply[:200],
            session,
            action_type="Gemini reply" if gemini_called else "sync reply",
            gemini_call="yes" if gemini_called else "no",
        )
    except Exception as e:
        # Catch any unhandled exceptions and return gracefully
        print(f"[LINE] Unhandled error in handle_line_message: {e}")
        try:
            _send_error_reply(event, "⚠️ 系統錯誤，請稍後再試。")
        except:
            pass


def handle_audio_message(event: MessageEvent[AudioMessage]):
    """
    1) Download LINE voicemail → save as ./voicemail/<user>_<ts>.m4a
    2) Upload to Drive (optional link in reply)
    3) Call Gemini STT (upload via Files API, then generate_content)
    4) Store transcription in session, set awaiting_stt_translation=True
    5) Reply with "原始轉錄：<text>\n請輸入欲翻譯之語言；若無，請輸入「無」或「new」。\n(Drive link)"
    """
    # Check concurrent audio processing limit
    global _active_audio_processing
    with _audio_lock:
        if _active_audio_processing >= MAX_CONCURRENT_AUDIO:
            _send_error_reply(event, "⚠️ 系統忙碌中，請稍後再試上傳語音。")
            return
        _active_audio_processing += 1
    
    try:
        user_id = event.source.user_id
        message_id = event.message.id
        session = get_user_session(user_id)

        # 🚫  Block audio uploads while editing Education sheets
        if session.get("mode") == "edu":
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=(
                        "⚠️ 目前在『衛教』模式，無法使用語音翻譯。\n"
                        "若要啟用語音功能，請點擊下方按鈕："
                    ),
                    quick_reply=QuickReply(items=create_quick_reply_items([("🆕 新對話", "new")]))
                )
            )
            return

        # 1. Download the raw audio from LINE with retry logic
        @exponential_backoff(
            max_retries=3,
            initial_delay=0.5,
            max_delay=10.0,
            exceptions=(LineBotApiError, ConnectionError, TimeoutError),
            on_retry=lambda attempt, error: print(f"[Audio Download] Retry {attempt} due to: {error}")
        )
        def download_audio():
            return line_bot_api.get_message_content(message_id)
        
        try:
            message_content = download_audio()
        except RetryError as e:
            print(f"[Audio Download] Failed after all retries: {e}")
            _send_error_reply(event, "⚠️ 無法下載語音檔，請稍後重試。網路連線似乎不穩定。")
            return
        except Exception as e:
            print(f"[Audio Download] Unexpected error: {e}")
            _send_error_reply(event, "⚠️ 下載語音檔時發生錯誤，請稍後重試。")
            return

        # 2. Save locally under ./voicemail/ with robust error handling
        # Validate user_id to prevent path traversal
        try:
            safe_user_id = sanitize_user_id(user_id)
        except ValueError as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 系統錯誤：無效的用戶ID")
            )
            return
        
        save_dir = VOICEMAIL_DIR
        save_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_user_id}_{timestamp}.m4a"
        
        # Create safe path to prevent directory traversal
        try:
            local_filename = Path(create_safe_path(str(save_dir), filename))
        except ValueError as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 系統錯誤：無法儲存語音檔案")
            )
            return

        # Enhanced file saving with chunked writing and connection stability
        total_size = 0
        chunk_size = 8192  # 8KB chunks
        max_retries_per_chunk = 3
        
        try:
            with open(local_filename, "wb") as f:
                chunk_iterator = message_content.iter_content(chunk_size=chunk_size)
                chunk_number = 0
                
                for chunk in chunk_iterator:
                    chunk_number += 1
                    retry_count = 0
                    
                    while retry_count < max_retries_per_chunk:
                        try:
                            if chunk:  # Filter out keep-alive chunks
                                total_size += len(chunk)
                                
                                # Check file size limit
                                if total_size > MAX_AUDIO_FILE_SIZE:
                                    f.close()
                                    local_filename.unlink(missing_ok=True)
                                    line_bot_api.reply_message(
                                        event.reply_token,
                                        TextSendMessage(text="⚠️ 語音檔過大（超過10MB），請縮短錄音長度。")
                                    )
                                    return
                                
                                f.write(chunk)
                                f.flush()  # Ensure data is written to disk
                                break  # Success, move to next chunk
                                
                        except (IOError, OSError) as e:
                            retry_count += 1
                            if retry_count >= max_retries_per_chunk:
                                raise Exception(f"Failed to write chunk {chunk_number} after {max_retries_per_chunk} retries: {e}")
                            print(f"[Audio Save] Retry {retry_count} for chunk {chunk_number}: {e}")
                            time.sleep(0.1 * retry_count)  # Brief delay before retry
                            
        except Exception as e:
            print(f"[Audio Save] Error saving audio file: {e}")
            # Clean up partial file
            if local_filename.exists():
                try:
                    local_filename.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[CLEANUP] Failed to delete temp file {local_filename}: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 儲存語音檔失敗，請稍後重試。")
            )
            return

        # 3. Call Gemini STT first (before upload)
        try:
            transcription = transcribe_audio_file(str(local_filename))
        except Exception as e:
            print(f"[STT ERROR] {e}")
            # BUG FIX: Clean up local file on STT failure
            try:
                if local_filename.exists():
                    local_filename.unlink()
            except Exception:
                pass
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 語音轉文字失敗，請稍後重試。")
            )
            return

        if not transcription:
            # Clean up file if transcription is empty
            try:
                if local_filename.exists():
                    local_filename.unlink()
                    print(f"[CLEANUP] Deleted file after empty transcription: {local_filename}")
            except Exception:
                pass
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 轉錄內容為空，無法處理。")
            )
            return

        # 5. Store transcription & set flag, then send prompt
        session["stt_transcription"] = transcription
        session["awaiting_stt_translation"] = True
        session["started"] = True          # NEW: fixes "speak"-first bug
        session.pop("awaiting_chat_language", None)        # NEW: avoid double prompt
        session["_prev_mode"] = session.get("mode") or "edu"  # remember current mode
        
        # 4. Upload to Drive and log to database
        # Note: upload_voicemail will delete the file after successful upload
        drive_link = None
        try:
            drive_link = upload_voicemail(
                str(local_filename), 
                user_id,
                transcription=transcription,
                translation=None  # Translation happens later
            )
        except Exception as e:
            print(f"[Voicemail upload/log failed] {e}")
            # Clean up file if upload fails
            try:
                if local_filename.exists():
                    local_filename.unlink()
                    print(f"[CLEANUP] Deleted file after upload failure: {local_filename}")
            except Exception as cleanup_error:
                print(f"[CLEANUP ERROR] Failed to delete {local_filename}: {cleanup_error}")
            # Continue even if upload fails

        reply_lines = [
            "📣 原始轉錄：",
            transcription
        ]
        #if drive_link:
        #    reply_lines.extend([
        #        "",
        #        f"🔗 已將語音檔上傳至 Google Drive：",
        #        drive_link
        #    ])

        # Add quick reply for voice translation options
        quick_reply = QuickReply(items=create_quick_reply_items(VOICE_TRANSLATION_OPTIONS))
        
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="\n".join(reply_lines), quick_reply=quick_reply)
            )
        except LineBotApiError:
            pass

        # Log audio message
        log_chat(
            user_id,
            "[AudioMessage]",
            transcription[:200],
            session,
            action_type="medchat_audio",
            gemini_call="yes",
        )
        
    finally:
        # Always decrement the counter
        with _audio_lock:
            _active_audio_processing -= 1