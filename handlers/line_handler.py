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
from utils.logging import log_chat
from services.gemini_service import references_to_flex
from services.stt_service import transcribe_audio_file
from utils.paths import VOICEMAIL_DIR
from utils.command_sets import create_quick_reply_items, MODE_SELECTION_OPTIONS, COMMON_LANGUAGES
from utils.validators import sanitize_user_id, sanitize_filename, create_safe_path
from utils.taigi_credit import create_taigi_credit_bubble
from utils.message_splitter import split_long_text, truncate_for_line, calculate_bubble_budget, MAX_BUBBLE_COUNT

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
        
        # Log interaction (skip for chat mode to avoid duplicates)
        if session.get("mode") != "chat":
            # Include context in user input for logging
            logged_input = user_input
            action_type = "sync reply"
            
            if session.get("awaiting_translate_language") or session.get("awaiting_chat_language"):
                # This input was a language selection
                logged_input = f"[Language: {user_input}] {user_input}"
            elif session.get("awaiting_email"):
                # This input was an email address
                logged_input = f"[Email to: {user_input}]"
                action_type = "Email sent" if "成功寄出" in reply_text else "Email failed"
                
                # Check if we have R2 URL from email upload
                email_r2_url = session.pop("email_r2_url", None)
            
            if gemini_called:
                action_type = "Gemini reply"
            
            # Use email R2 URL if available, otherwise use regular gemini URL logic
            gemini_url = None
            if 'email_r2_url' in locals() and email_r2_url:
                gemini_url = email_r2_url
                
            log_chat(
                user_id,
                logged_input,
                reply_text[:200],
                session,
                action_type=action_type,
                gemini_call="yes" if gemini_called else "no",
                gemini_output_url=gemini_url
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
    
    # Only allow audio in chat mode after language is selected
    if session.get("mode") != "chat" or not session.get("chat_target_lang"):
        # Provide appropriate message based on current state
        if not session.get("started"):
            message = "請先點擊【開始】選擇功能："
            options = [("🆕 開始", "new")]
        elif session.get("mode") == "edu":
            message = "衛教模式不支援語音功能。請切換至醫療翻譯模式："
            options = [("🆕 新對話", "new")]
        elif session.get("mode") == "chat" and session.get("awaiting_chat_language"):
            message = "請先選擇翻譯語言後，才能使用語音功能："
            options = []  # Will show language options
        else:
            message = "語音功能僅在醫療翻譯模式中可用。請先選擇功能："
            options = MODE_SELECTION_OPTIONS
        
        reply_msg = TextSendMessage(text=message)
        if options:
            reply_msg.quick_reply = QuickReply(items=create_quick_reply_items(options))
        elif session.get("awaiting_chat_language"):
            reply_msg.quick_reply = QuickReply(items=create_quick_reply_items(COMMON_LANGUAGES))
            
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    try:
        # Download audio
        audio_content = line_bot_api.get_message_content(message_id)
        
        # Save audio file temporarily for transcription only
        audio_path = save_audio_file(user_id, audio_content)
        if not audio_path:
            raise Exception("Failed to save audio")
        
        # Transcribe audio
        transcription = transcribe_audio_file(str(audio_path))
        
        if not transcription:
            raise Exception("Failed to transcribe audio")
        
        # Delete audio file immediately - no uploads
        try:
            audio_path.unlink()
        except:
            pass
        
        # Process transcription exactly like text input through medchat
        from handlers.medchat_handler import handle_medchat
        reply_text, gemini_called, quick_reply_data = handle_medchat(user_id, transcription, session)
        
        # Add voicemail indicator to show it came from voice
        response_text = f"🎤 語音訊息：\n{transcription}\n\n{reply_text}"
        
        # Create response bubbles
        bubbles = create_message_bubbles(session, response_text, quick_reply_data, gemini_called)
        
        # Send response
        if bubbles:
            line_bot_api.reply_message(event.reply_token, bubbles)
            
    except Exception as e:
        print(f"[Audio] Error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="語音處理失敗。")
        )

def create_message_bubbles(session: dict, reply_text: str, quick_reply_data: Optional[dict], gemini_called: bool) -> List:
    """Create message bubbles based on session state"""
    bubbles = []
    
    # Check if we need to show Taigi credit with audio
    show_taigi_credit = session.pop("show_taigi_credit", False)
    
    # Handle TTS audio with credit for Taigi
    if session.get("tts_audio_url") and show_taigi_credit:
        # Show audio with credit bubble for Taigi
        # 1. Credit bubble
        credit_bubble = create_taigi_credit_bubble()
        bubbles.append(FlexSendMessage(alt_text="台語語音技術提供", contents=credit_bubble))
        
        # 2. TTS audio
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
        
        # Education mode content - only show when Gemini was actually called
        elif session.get("mode") == "edu" and gemini_called:
            # Only show content bubbles when new content is generated
            zh_content = session.get("zh_output", "")
            translated_content = session.get("translated_output", "")
            just_translated = session.pop("just_translated", False)
            
            # Calculate bubble budget
            has_references = bool(session.get("references", []))
            has_audio = bool(session.get("tts_audio_url"))
            has_taigi_credit = show_taigi_credit
            available_bubbles = calculate_bubble_budget(has_references, has_audio, has_taigi_credit)
            
            # Add content based on what action was performed
            if just_translated and translated_content:
                # Show only translated content after translation
                chunks = split_long_text(translated_content, "🌐 譯文：\n", available_bubbles)
                for chunk in chunks:
                    bubbles.append(TextSendMessage(text=chunk))
            elif zh_content and not just_translated:
                # Show only Chinese content for initial generation or modification
                chunks = split_long_text(zh_content, "📄 原文：\n", available_bubbles)
                for chunk in chunks:
                    bubbles.append(TextSendMessage(text=chunk))
    
    # Add references only when showing edu content (new generation, modify, or translate)
    if session.get("mode") == "edu" and gemini_called:
        refs = session.get("references", [])
        if refs:
            flex = references_to_flex(refs)
            if flex:
                bubbles.append(FlexSendMessage(alt_text="參考來源", contents=flex))
    
    # Add main reply (ensure it fits LINE's limits)
    truncated_reply = truncate_for_line(reply_text)
    if quick_reply_data:
        bubbles.append(
            TextSendMessage(
                text=truncated_reply,
                quick_reply=QuickReply(items=quick_reply_data["items"])
            )
        )
    else:
        bubbles.append(TextSendMessage(text=truncated_reply))
    
    # Ensure we never exceed LINE's bubble limit per message
    if len(bubbles) > MAX_BUBBLE_COUNT:
        print(f"⚠️ [LINE] Warning: {len(bubbles)} bubbles created, truncating to {MAX_BUBBLE_COUNT}")
        # Keep the main reply (last bubble) and as many content bubbles as possible
        main_reply = bubbles[-1]
        content_bubbles = bubbles[:-1][:MAX_BUBBLE_COUNT-1]  # Keep up to 4 content bubbles
        bubbles = content_bubbles + [main_reply]
    
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