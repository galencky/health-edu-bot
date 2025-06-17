"""
LINE Bot Message Handler - Clean Version
Handles incoming LINE messages (text and audio) with clear separation of concerns
"""
import os
import time
import asyncio
import threading
from pathlib import Path
from typing import List, Optional, Tuple

from linebot import LineBotApi
from linebot.models import (
    TextSendMessage, FlexSendMessage, AudioSendMessage,
    MessageEvent, TextMessage, AudioMessage, QuickReply
)
from linebot.exceptions import LineBotApiError

from handlers.logic_handler import handle_user_message
from handlers.session_manager import get_user_session
from utils.logging import log_chat, upload_voicemail
from utils.google_drive_service import upload_stt_translation_log
from services.gemini_service import references_to_flex, _call_genai
from services.stt_service import transcribe_audio_file
from utils.paths import VOICEMAIL_DIR
from utils.command_sets import (
    new_commands, create_quick_reply_items, 
    VOICE_TRANSLATION_OPTIONS, TTS_OPTIONS, COMMON_LANGUAGES
)
from utils.retry_utils import exponential_backoff, RetryError
from utils.validators import sanitize_user_id, sanitize_filename, create_safe_path

# ============================================================
# CONFIGURATION
# ============================================================

# File size limits
MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Concurrency control
MAX_CONCURRENT_AUDIO = 3
_active_audio_processing = 0
_audio_lock = threading.Lock()

# Prompts
VOICEMAIL_TRANSLATION_PROMPT = """
You are a medical translation assistant fluent in {lang}. 
Please translate the following message to {lang}.
"""

# LINE client
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def split_long_text(text: str, max_length: int = 4000) -> List[str]:
    """Split long text into chunks that fit LINE's message limit"""
    if not text:
        return []
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def send_error_message(event: MessageEvent, error_text: str) -> None:
    """Send error message to user with fallback handling"""
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=error_text)
        )
    except Exception as e:
        print(f"[LINE ERROR] Failed to send error message: {e}")


def create_message_bubbles(
    session: dict,
    reply_text: str,
    quick_reply_data: Optional[dict],
    gemini_called: bool
) -> List:
    """
    Create message bubbles based on session state
    
    Returns:
        List of LINE message objects to send
    """
    bubbles = []
    
    # Mode 1: Chat mode with TTS audio
    if session.get("mode") == "chat" and session.get("tts_audio_url"):
        # Add audio message
        bubbles.append(
            AudioSendMessage(
                original_content_url=session.pop("tts_audio_url"),
                duration=session.pop("tts_audio_dur", 0)
            )
        )
        
        # Add text with quick reply
        if quick_reply_data:
            bubbles.append(
                TextSendMessage(
                    text=reply_text,
                    quick_reply=QuickReply(items=quick_reply_data["items"])
                )
            )
        else:
            bubbles.append(TextSendMessage(text=reply_text))
    
    # Mode 2: Education mode with content display
    elif session.get("mode") == "edu":
        # Show content when available
        if gemini_called or session.get("zh_output") or session.get("translated_output"):
            _add_education_content_bubbles(bubbles, session, gemini_called)
        
        # Always add reply with quick reply
        if quick_reply_data:
            bubbles.append(
                TextSendMessage(
                    text=reply_text,
                    quick_reply=QuickReply(items=quick_reply_data["items"])
                )
            )
        else:
            bubbles.append(TextSendMessage(text=reply_text))
    
    # Mode 3: Default mode
    else:
        if quick_reply_data:
            bubbles.append(
                TextSendMessage(
                    text=reply_text,
                    quick_reply=QuickReply(items=quick_reply_data["items"])
                )
            )
        else:
            bubbles.append(TextSendMessage(text=reply_text))
    
    return bubbles


def _add_education_content_bubbles(
    bubbles: List,
    session: dict,
    gemini_called: bool
) -> None:
    """Add education content bubbles (helper for create_message_bubbles)"""
    zh_content = session.get("zh_output", "")
    translated_content = session.get("translated_output", "")
    
    # Only show content text when newly generated
    if gemini_called and (zh_content or translated_content):
        # Split content into chunks
        zh_chunks = split_long_text(f"📄 原文：\n{zh_content}")[:2] if zh_content else []
        tr_chunks = split_long_text(f"🌐 譯文：\n{translated_content}")
        
        # Limit translation chunks based on remaining space
        tr_chunks = tr_chunks[:max(0, 3 - len(zh_chunks))] if tr_chunks else []
        
        # Add content bubbles
        for chunk in zh_chunks + tr_chunks:
            bubbles.append(TextSendMessage(text=chunk))
        
        # Add overflow warning if needed
        if len(zh_chunks) + len(tr_chunks) > 3:
            bubbles.append(
                TextSendMessage(
                    text="⚠️ 內容過長，僅部分顯示。如需完整內容請點擊下方按鈕：",
                    quick_reply=QuickReply(
                        items=create_quick_reply_items([("📧 寄送", "mail")])
                    )
                )
            )
    
    # Always show references if available
    references = session.get("references", [])
    if references:
        flex_content = references_to_flex(references)
        if flex_content:
            bubbles.append(
                FlexSendMessage(alt_text="參考來源", contents=flex_content)
            )


# ============================================================
# MAIN HANDLERS
# ============================================================

def handle_line_message(event: MessageEvent[TextMessage]) -> None:
    """
    Handle incoming text messages from LINE
    
    Flow:
    1. Get user session
    2. Process message through logic handler
    3. Create and send response bubbles
    4. Log interaction
    """
    try:
        # Extract user info
        user_id = event.source.user_id
        user_input = event.message.text
        
        # Get session and process message
        session = get_user_session(user_id)
        reply_text, gemini_called, quick_reply_data = handle_user_message(
            user_id, user_input, session
        )
        
        # Create response bubbles
        bubbles = create_message_bubbles(
            session, reply_text, quick_reply_data, gemini_called
        )
        
        # Send response
        if bubbles:
            try:
                line_bot_api.reply_message(event.reply_token, bubbles)
            except LineBotApiError as e:
                # Fallback to simple error message
                send_error_message(event, f"⚠️ 發送訊息失敗：{e}")
        
        # Log interaction (skip for chat mode as it logs itself)
        if session.get("mode") != "chat":
            action_type = "Gemini reply" if gemini_called else "sync reply"
            gemini_call = "yes" if gemini_called else "no"
            
            log_chat(
                user_id,
                user_input,
                reply_text[:200],  # Truncate for logging
                session,
                action_type=action_type,
                gemini_call=gemini_call
            )
    
    except Exception as e:
        print(f"[LINE ERROR] Unhandled error in handle_line_message: {e}")
        send_error_message(event, "⚠️ 系統錯誤，請稍後再試。")


def handle_audio_message(event: MessageEvent[AudioMessage]) -> None:
    """
    Handle incoming audio messages (voicemail feature)
    
    Flow:
    1. Check concurrency limit
    2. Download and save audio
    3. Transcribe using STT
    4. Set up for translation
    5. Upload to Drive
    """
    # Check concurrency limit
    with _audio_lock:
        global _active_audio_processing
        if _active_audio_processing >= MAX_CONCURRENT_AUDIO:
            send_error_message(event, "⚠️ 系統忙碌中，請稍後再試上傳語音。")
            return
        _active_audio_processing += 1
    
    try:
        _process_audio_message(event)
    finally:
        # Always decrement counter
        with _audio_lock:
            _active_audio_processing -= 1


def _process_audio_message(event: MessageEvent[AudioMessage]) -> None:
    """Process audio message (separated for cleaner error handling)"""
    user_id = event.source.user_id
    message_id = event.message.id
    session = get_user_session(user_id)
    
    # Block audio in education mode
    if session.get("mode") == "edu":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="⚠️ 目前在『衛教』模式，無法使用語音翻譯。\n若要啟用語音功能，請點擊下方按鈕：",
                quick_reply=QuickReply(
                    items=create_quick_reply_items([("🆕 新對話", "new")])
                )
            )
        )
        return
    
    # Download audio with retry
    audio_content = _download_audio_with_retry(message_id)
    if not audio_content:
        send_error_message(event, "⚠️ 無法下載語音檔，請稍後重試。")
        return
    
    # Save audio file
    audio_path = _save_audio_file(user_id, audio_content)
    if not audio_path:
        send_error_message(event, "⚠️ 儲存語音檔失敗，請稍後重試。")
        return
    
    # Transcribe audio
    transcription = _transcribe_audio(audio_path)
    if not transcription:
        send_error_message(event, "⚠️ 語音辨識失敗，請確保語音清晰。")
        _cleanup_audio_file(audio_path)
        return
    
    # Upload to Drive
    drive_link = _upload_audio_to_drive(audio_path, user_id, transcription)
    
    # Update session
    session.update({
        "awaiting_stt_translation": True,
        "stt_transcription": transcription,
        "_prev_mode": session.get("mode"),
        "mode": None
    })
    
    # Send response
    response_text = f"🎤 原始轉錄：\n{transcription}\n\n請選擇翻譯語言："
    if drive_link:
        response_text += f"\n\n🔗 語音檔連結：{drive_link}"
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=response_text,
            quick_reply=QuickReply(items=create_quick_reply_items(VOICE_TRANSLATION_OPTIONS))
        )
    )
    
    # Log the audio message interaction
    log_chat(
        user_id,
        "[AudioMessage]",
        transcription[:200],
        session,
        action_type="medchat_audio",
        gemini_call="yes"
    )


# ============================================================
# AUDIO PROCESSING HELPERS
# ============================================================

def _download_audio_with_retry(message_id: str):
    """Download audio from LINE with retry logic"""
    @exponential_backoff(
        max_retries=3,
        initial_delay=0.5,
        max_delay=10.0,
        exceptions=(LineBotApiError, ConnectionError, TimeoutError),
        on_retry=lambda attempt, error: print(f"[Audio] Retry {attempt}: {error}")
    )
    def download():
        return line_bot_api.get_message_content(message_id)
    
    try:
        return download()
    except Exception as e:
        print(f"[Audio] Download failed: {e}")
        return None


def _save_audio_file(user_id: str, audio_content) -> Optional[Path]:
    """Save audio content to file with validation"""
    try:
        # Validate user ID
        safe_user_id = sanitize_user_id(user_id)
        
        # Create filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_user_id}_{timestamp}.m4a"
        
        # Create safe path
        save_dir = VOICEMAIL_DIR
        save_dir.mkdir(exist_ok=True)
        filepath = Path(create_safe_path(str(save_dir), filename))
        
        # Save with size validation
        total_size = 0
        with open(filepath, "wb") as f:
            for chunk in audio_content.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    if total_size > MAX_AUDIO_FILE_SIZE:
                        filepath.unlink(missing_ok=True)
                        return None
                    f.write(chunk)
        
        return filepath
    
    except Exception as e:
        print(f"[Audio] Save failed: {e}")
        return None


def _transcribe_audio(audio_path: Path) -> Optional[str]:
    """Transcribe audio file using STT service"""
    try:
        result = transcribe_audio_file(str(audio_path))
        if result and result.get("text"):
            return result["text"]
        return None
    except Exception as e:
        print(f"[Audio] Transcription failed: {e}")
        return None


def _upload_audio_to_drive(
    audio_path: Path,
    user_id: str,
    transcription: str
) -> Optional[str]:
    """Upload audio to Google Drive"""
    try:
        drive_link = upload_voicemail(
            str(audio_path),
            user_id,
            transcription=transcription
        )
        return drive_link
    except Exception as e:
        print(f"[Audio] Drive upload failed: {e}")
        return None


def _cleanup_audio_file(audio_path: Path) -> None:
    """Clean up temporary audio file"""
    try:
        if audio_path.exists():
            audio_path.unlink()
    except Exception as e:
        print(f"[Audio] Cleanup failed: {e}")