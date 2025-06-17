"""
LINE Bot Message Handler
"""
import os
import time
from pathlib import Path
from typing import List, Optional

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
from services.gemini_service import references_to_flex
from services.stt_service import transcribe_audio_file
from utils.paths import VOICEMAIL_DIR
from utils.command_sets import create_quick_reply_items, VOICE_TRANSLATION_OPTIONS
from utils.validators import sanitize_user_id, sanitize_filename, create_safe_path
from utils.taigi_credit import create_taigi_credit_bubble

# Configuration
MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024  # 10MB
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

def handle_line_message(event: MessageEvent) -> None:
    """Handle incoming text messages from LINE"""
    try:
        user_id = event.source.user_id
        user_input = event.message.text
        
        # Get session and process message
        session = get_user_session(user_id)
        reply_text, gemini_called, quick_reply_data = handle_user_message(
            user_id, user_input, session
        )
        
        # Create response bubbles
        bubbles = create_message_bubbles(session, reply_text, quick_reply_data, gemini_called)
        
        # Send response
        if bubbles:
            line_bot_api.reply_message(event.reply_token, bubbles)
        
        # Log interaction
        if session.get("mode") != "chat":
            # Include language selection in user input for logging
            logged_input = user_input
            if session.get("awaiting_translate_language") or session.get("awaiting_chat_language"):
                # This input was a language selection
                logged_input = f"[Language: {user_input}] {user_input}"
            
            log_chat(
                user_id,
                logged_input,
                reply_text[:200],
                session,
                action_type="Gemini reply" if gemini_called else "sync reply",
                gemini_call="yes" if gemini_called else "no"
            )
    
    except Exception as e:
        print(f"[LINE ERROR] {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="系統發生錯誤，請稍後再試。")
        )

def handle_audio_message(event: MessageEvent) -> None:
    """Handle incoming audio messages (voicemail feature)"""
    user_id = event.source.user_id
    message_id = event.message.id
    session = get_user_session(user_id)
    
    # Block audio in education mode
    if session.get("mode") == "edu":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="衛教模式不支援語音翻譯功能。如需使用語音功能，請點擊【新對話】切換至醫療翻譯模式：",
                quick_reply=QuickReply(
                    items=create_quick_reply_items([("🆕 新對話", "new")])
                )
            )
        )
        return
    
    try:
        # Download audio
        audio_content = line_bot_api.get_message_content(message_id)
        
        # Save audio file
        audio_path = save_audio_file(user_id, audio_content)
        if not audio_path:
            raise Exception("Failed to save audio")
        
        # Transcribe audio
        transcription = transcribe_audio_file(str(audio_path))
        
        if not transcription:
            raise Exception("Failed to transcribe audio")
        
        # Upload to Drive
        drive_link = upload_voicemail(str(audio_path), user_id, transcription=transcription)
        
        # Update session
        session["awaiting_stt_translation"] = True
        session["stt_transcription"] = transcription
        session["_prev_mode"] = session.get("mode")
        session["mode"] = None
        
        # Send response
        response_text = f"🎤 原始轉錄：\n{transcription}\n\n請選擇或輸入您需要的翻譯語言（支援各種語言）："
#        if drive_link:
#            response_text += f"\n\n🔗 語音檔連結：{drive_link}"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=response_text,
                quick_reply=QuickReply(items=create_quick_reply_items(VOICE_TRANSLATION_OPTIONS))
            )
        )
        
        # Log interaction
        log_chat(user_id, "[AudioMessage]", transcription[:200], session, 
                action_type="medchat_audio", gemini_call="yes")
        
        # Cleanup
        try:
            audio_path.unlink()
        except:
            pass
            
    except Exception as e:
        print(f"[Audio] Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="語音處理失敗。")
        )

def create_message_bubbles(session: dict, reply_text: str, quick_reply_data: Optional[dict], gemini_called: bool) -> List:
    """Create message bubbles based on session state"""
    bubbles = []
    
    # Check if this is a Taigi translation with TTS
    target_lang = session.get("last_translation_lang") or session.get("chat_target_lang")
    is_taigi = target_lang in ["台語", "臺語", "taiwanese", "taigi"]
    has_taigi_tts = is_taigi and session.get("tts_audio_url")
    
    # Special handling for Taigi: combine translation + credit + TTS in one message
    if has_taigi_tts:
        # 1. Translation text
        translated_content = session.get("translated_output", "")
        if translated_content:
            bubbles.append(TextSendMessage(text=f"🌐 台語翻譯：\n{translated_content}"))
        
        # 2. Credit bubble
        credit_bubble = create_taigi_credit_bubble()
        bubbles.append(FlexSendMessage(alt_text="台語語音技術提供", contents=credit_bubble))
        
        # 3. TTS audio
        bubbles.append(
            AudioSendMessage(
                original_content_url=session.pop("tts_audio_url"),
                duration=session.pop("tts_audio_dur", 0)
            )
        )
    else:
        # Regular flow for non-Taigi or Taigi without TTS
        
        # TTS audio (for chat mode OR STT translation with TTS)
        if session.get("tts_audio_url"):
            bubbles.append(
                AudioSendMessage(
                    original_content_url=session.pop("tts_audio_url"),
                    duration=session.pop("tts_audio_dur", 0)
                )
            )
        
        # Education mode content
        elif session.get("mode") == "edu":
            # For Taigi translations in edu mode, they're handled above
            if not is_taigi and (gemini_called or session.get("translated_output")):
                zh_content = session.get("zh_output", "")
                translated_content = session.get("translated_output", "")
                
                # Add content if newly generated
                if zh_content or translated_content:
                    content_text = ""
                    if zh_content:
                        content_text += f"📄 原文：\n{zh_content[:2000]}\n\n"
                    if translated_content:
                        content_text += f"🌐 譯文：\n{translated_content[:2000]}"
                    
                    if content_text:
                        bubbles.append(TextSendMessage(text=content_text.strip()))
    
    # Add references only when showing edu content (new generation, modify, or translate)
    if session.get("mode") == "edu" and gemini_called:
        refs = session.get("references", [])
        if refs:
            flex = references_to_flex(refs)
            if flex:
                bubbles.append(FlexSendMessage(alt_text="參考來源", contents=flex))
    
    # Add main reply
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

def save_audio_file(user_id: str, audio_content) -> Optional[Path]:
    """Save audio content to file"""
    try:
        safe_user_id = sanitize_user_id(user_id)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_user_id}_{timestamp}.m4a"
        
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