"""
Message Logic Handler - Processes user messages and determines responses
"""
from typing import Tuple, Optional, Dict, List
import re
import dns.resolver

from services.tts_service import synthesize
from services.gemini_service import (
    call_zh, call_translate, plainify, confirm_translate, get_references
)
from services.taigi_service import translate_to_taigi, synthesize_taigi
from services.prompt_config import modify_prompt
from handlers.mail_handler import send_last_txt_email
from handlers.medchat_handler import handle_medchat
from utils.validators import sanitize_text, validate_email
from utils.language_utils import normalize_language_input
from utils.command_sets import (
    new_commands, edu_commands, chat_commands, modify_commands,
    translate_commands, mail_commands, speak_commands,
    create_quick_reply_items, MODE_SELECTION_OPTIONS,
    COMMON_LANGUAGES, EDU_LANGUAGES, COMMON_DISEASES, TTS_OPTIONS,
    CHAT_CONTINUE_OPTIONS
)

# ============================================================
# MAIN HANDLER
# ============================================================

def handle_user_message(
    user_id: str,
    text: str,
    session: Dict
) -> Tuple[str, bool, Optional[Dict]]:
    """
    Main message dispatcher
    Returns: (reply_text, gemini_called, quick_reply_data)
    """
    text = text.strip()
    text_lower = text.lower()
    
    # Store user_id in session for logging
    session["user_id"] = user_id
    
    # Handle 'new' command
    if text_lower in new_commands:
        return handle_new_command(session)
    
    # Handle 'speak' command
    if session.get("started") and text_lower in speak_commands:
        return handle_speak_command(session, user_id)
    
    # Handle unstarted session
    if not session.get("started"):
        quick_reply = {"items": create_quick_reply_items([("🆕 開始", "new")])}
        return "歡迎使用 MedEdBot！請點擊【開始】按鈕開始使用：", False, quick_reply
    
    # Handle mode selection
    if session.get("mode") is None:
        # Education mode
        if text_lower in edu_commands:
            session["mode"] = "edu"
            quick_reply = {"items": create_quick_reply_items(COMMON_DISEASES)}
            return "📚 進入衛教模式。請選擇或輸入您想了解的健康主題（如：糖尿病、高血壓等）：\n(AI 生成約需 20 秒，請耐心等候)", False, quick_reply
        
        # Chat mode
        if text_lower in chat_commands:
            session["mode"] = "chat"
            session["awaiting_chat_language"] = True
            quick_reply = {"items": create_quick_reply_items(COMMON_LANGUAGES)}
            return "💬 進入對話模式。請選擇或輸入您需要的翻譯語言：", False, quick_reply
        
        # Default
        quick_reply = {"items": create_quick_reply_items(MODE_SELECTION_OPTIONS)}
        return "請選擇您需要的功能，或直接發送語音訊息：", False, quick_reply
    
    # Handle education mode
    if session.get("mode") == "edu":
        return handle_education_mode(session, text, text_lower, user_id)
    
    # Handle chat mode
    if session.get("mode") == "chat":
        return handle_medchat(user_id, text, session)
    
    # Fallback
    quick_reply = {"items": create_quick_reply_items([("🆕 開始", "new")])}
    return "抱歉，我不太理解您的意思。請點擊【開始】重新選擇功能，或直接發送語音訊息。", False, quick_reply

# ============================================================
# COMMAND HANDLERS
# ============================================================

def handle_new_command(session: Dict) -> Tuple[str, bool, Optional[Dict]]:
    """Reset session and start over"""
    session.clear()
    session["started"] = True
    quick_reply = {"items": create_quick_reply_items(MODE_SELECTION_OPTIONS)}
    return "請選擇您需要的功能：", False, quick_reply

def handle_speak_command(session: Dict, user_id: str) -> Tuple[str, bool, Optional[Dict]]:
    """Generate TTS audio"""
    if session.get("mode") == "edu":
        quick_reply = {"items": create_quick_reply_items([("🆕 新對話", "new")])}
        return "衛教模式不支援語音朗讀功能。如需使用語音功能，請點擊【新對話】切換至醫療翻譯模式。", False, quick_reply
    
    # Check if TTS audio already exists
    if session.get("tts_audio_url"):
        if session.get("mode") == "chat":
            quick_reply = {"items": create_quick_reply_items(CHAT_CONTINUE_OPTIONS)}
        else:
            quick_reply = {"items": create_quick_reply_items([("🆕 新對話", "new")])}
        return "🔊 語音檔已存在", False, quick_reply
    
    tts_source = session.get("translated_output")
    if not tts_source:
        return "目前沒有可朗讀的翻譯內容。請先進行翻譯後再使用朗讀功能。", False, None
    
    try:
        # Check if last translation was to Taiwanese
        last_lang = session.get("last_translation_lang", "") or session.get("chat_target_lang", "")
        if last_lang in ["台語", "臺語", "taiwanese", "taigi"]:
            # For Taiwanese, we need the original Chinese text
            zh_source = session.get("zh_output", "")
            if not zh_source:
                return "無法找到原始中文內容進行台語語音合成。", False, None
            url, duration = synthesize_taigi(zh_source, user_id)
            # Set flag to show credit bubble with audio
            session["show_taigi_credit"] = True
        else:
            # Use regular TTS for other languages
            url, duration = synthesize(tts_source, user_id)
        
        session["tts_audio_url"] = url
        session["tts_audio_dur"] = duration
        
        # Use continue options for chat mode
        if session.get("mode") == "chat":
            quick_reply = {"items": create_quick_reply_items(CHAT_CONTINUE_OPTIONS)}
        else:
            quick_reply = {"items": create_quick_reply_items([("🆕 新對話", "new")])}
        return "🔊 語音檔已生成", False, quick_reply
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return "語音合成時發生錯誤，請稍後再試。", False, None


# ============================================================
# EDUCATION MODE
# ============================================================

def handle_education_mode(session: Dict, text: str, text_lower: str, user_id: str) -> Tuple[str, bool, Optional[Dict]]:
    """Handle education mode logic"""
    # Check awaiting states first
    if session.get("awaiting_modify"):
        return handle_modify_response(session, text)
    
    if session.get("awaiting_translate_language"):
        return handle_translate_response(session, text, user_id)
    
    if session.get("awaiting_email"):
        return handle_email_response(session, text, user_id)
    
    # Check commands
    if text_lower in modify_commands:
        if not session.get("zh_output"):
            return "目前沒有衛教內容可供修改。請先輸入健康主題產生內容。", False, None
        session["awaiting_modify"] = True
        return "✏️ 請描述您想如何修改內容：\n(AI 處理約需 20 秒，請耐心等候)", False, None
    
    if text_lower in translate_commands:
        if not session.get("zh_output"):
            return "目前沒有衛教內容可供翻譯。請先輸入衛教主題產生內容。", False, None
        session["awaiting_translate_language"] = True
        quick_reply = {"items": create_quick_reply_items(EDU_LANGUAGES)}
        return "🌐 請選擇或輸入任何您需要的翻譯語言：\n(AI 翻譯約需 20 秒，請耐心等候)", False, quick_reply
    
    if text_lower in mail_commands:
        if not session.get("zh_output"):
            return "目前沒有衛教內容可供寄送。請先輸入衛教主題產生內容。", False, None
        session["awaiting_email"] = True
        return "📧 請輸入收件人的 email 地址（例如：example@gmail.com）：", False, None
    
    # Generate content if none exists
    if not session.get("zh_output"):
        zh_content = call_zh(text)
        session["zh_output"] = zh_content
        session["last_topic"] = text[:30]
        
        # Get references
        refs = get_references()
        if refs:
            if session.get("references"):
                session["references"].extend(refs)
            else:
                session["references"] = refs
        
        quick_reply = {"items": create_quick_reply_items([
            ("✏️ 修改", "modify"),
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])}
        return "✅ 中文版衛教內容已生成。", True, quick_reply
    
    # Fallback
    quick_reply = {"items": create_quick_reply_items([
        ("🆕 開始", "new"),
        ("✏️ 修改", "modify"),
        ("🌐 翻譯", "translate"),
        ("📧 寄送", "mail")
    ])}
    return "請選擇您想執行的操作，或直接輸入健康主題查詢新內容：", False, quick_reply

def handle_modify_response(session: Dict, instruction: str) -> Tuple[str, bool, Optional[Dict]]:
    """Process content modification"""
    prompt = f"User instruction:\n{instruction}\n\nOriginal content:\n{session['zh_output']}"
    new_content = call_zh(prompt, system_prompt=modify_prompt)
    
    session["zh_output"] = new_content
    session["awaiting_modify"] = False
    
    # Update references
    refs = get_references()
    if refs:
        if session.get("references"):
            session["references"].extend(refs)
        else:
            session["references"] = refs
    
    quick_reply = {"items": create_quick_reply_items([
        ("✏️ 修改", "modify"),
        ("🌐 翻譯", "translate"),
        ("📧 寄送", "mail"),
        ("🆕 新對話", "new")
    ])}
    return "✅ 內容已根據您的要求修改。", True, quick_reply

def handle_translate_response(session: Dict, language: str, user_id: str = "unknown") -> Tuple[str, bool, Optional[Dict]]:
    """Process translation"""
    language = normalize_language_input(language)
    
    # No need to validate - Gemini supports all languages
    if not language or not language.strip():
        quick_reply = {"items": create_quick_reply_items(EDU_LANGUAGES)}
        return "請輸入或選擇您需要的翻譯語言：", False, quick_reply
    
    # Block Taigi in education mode to prevent overloading the service
    if language in ["台語", "臺語", "taiwanese", "taigi"]:
        quick_reply = {"items": create_quick_reply_items(EDU_LANGUAGES)}
        return "衛教模式不支援台語翻譯。請選擇其他語言，或使用醫療翻譯模式進行台語翻譯。", False, quick_reply
    
    # Use Gemini for all languages in edu mode
    translated = call_translate(session["zh_output"], language)
    gemini_called = True
    
    # Update references only for Gemini calls
    refs = get_references()
    if refs:
        if session.get("references"):
            session["references"].extend(refs)
        else:
            session["references"] = refs
    
    session["translated_output"] = translated
    session["translated"] = True
    session["awaiting_translate_language"] = False
    session["last_translation_lang"] = language
    
    quick_reply = {"items": create_quick_reply_items([
        ("🌐 翻譯", "translate"),
        ("📧 寄送", "mail"),
        ("🆕 新對話", "new")
    ])}
    return f"🌐 翻譯完成（目標語言：{language}）。", gemini_called, quick_reply

def handle_email_response(session: Dict, email: str, user_id: str = "unknown") -> Tuple[str, bool, Optional[Dict]]:
    """Process email sending"""
    try:
        validated_email = validate_email(email)
        domain = validated_email.split("@")[1]
        
        # Check MX record
        try:
            dns.resolver.resolve(domain, "MX", lifetime=3)
        except:
            return f"無法驗證 {domain} 的郵件伺服器。請確認 email 地址是否正確（例如：name@gmail.com）。", False, None
    
    except ValueError as e:
        return f"輸入的 email 格式不正確：{e}\n請輸入有效的 email 地址（例如：name@gmail.com）。", False, None
    
    session["awaiting_email"] = False
    success = send_last_txt_email(user_id, validated_email, session)
    
    if success:
        quick_reply = {"items": create_quick_reply_items([
            ("📧 寄送", "mail"),
            ("🌐 翻譯", "translate"),
            ("🆕 新對話", "new")
        ])}
        return f"✅ 已成功寄出衛教內容至 {validated_email}", False, quick_reply
    else:
        return "郵件寄送失敗。請檢查網路連線後再試一次。", False, None

# ============================================================
# HELPER FUNCTIONS
# ============================================================

