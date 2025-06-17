"""
Central Message Logic Handler - Clean Version
Processes user messages and determines appropriate responses
"""
from typing import Tuple, Optional, Dict, List
import re
import dns.resolver

from services.tts_service import synthesize
from services.gemini_service import (
    call_zh, call_translate, plainify, confirm_translate, get_references
)
from services.prompt_config import modify_prompt
from handlers.mail_handler import send_last_txt_email
from handlers.medchat_handler import handle_medchat
from utils.google_drive_service import upload_stt_translation_log
from utils.validators import sanitize_text, validate_email, validate_language_code
from utils.command_sets import (
    new_commands, edu_commands, chat_commands, modify_commands,
    translate_commands, mail_commands, speak_commands,
    create_quick_reply_items, MODE_SELECTION_OPTIONS,
    COMMON_LANGUAGES, COMMON_DISEASES, TTS_OPTIONS
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check_mx_record(domain: str) -> bool:
    """Check if email domain has valid MX records"""
    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=3))
    except Exception:
        return False


def create_quick_reply(items: List[Tuple[str, str]]) -> Dict:
    """Create quick reply configuration"""
    return {"items": create_quick_reply_items(items)}


def update_session_references(session: Dict, new_refs: List[Dict]) -> None:
    """Update session references list"""
    if not new_refs:
        return
    
    if session.get("references"):
        session["references"].extend(new_refs)
    else:
        session["references"] = new_refs


def normalize_language_input(text: str) -> str:
    """Normalize language input for better matching"""
    text = text.strip().lower()
    
    # Common substitutions
    replacements = {
        "台語": "臺語",
        "台灣": "臺灣",
        "中文": "中文(繁體)",
        "english": "英文",
        "japanese": "日文",
        "thai": "泰文",
        "vietnamese": "越南文",
        "indonesian": "印尼文"
    }
    
    for old, new in replacements.items():
        if old in text:
            return new
    
    return text


# ============================================================
# COMMAND HANDLERS
# ============================================================

class CommandHandler:
    """Base class for command handlers"""
    
    @staticmethod
    def handle_new_command(session: Dict) -> Tuple[str, bool, Optional[Dict]]:
        """Handle 'new' command - reset session"""
        session.clear()
        session.update({
            "started": True,
            "mode": None,
            # Initialize all session fields
            "zh_output": None,
            "translated_output": None,
            "translated": False,
            "awaiting_translate_language": False,
            "awaiting_email": False,
            "awaiting_modify": False,
            "last_topic": None,
            "last_translation_lang": None,
            "references": None,
            "awaiting_chat_language": False,
            "chat_target_lang": None,
            "awaiting_stt_translation": False,
            "stt_transcription": None,
            "stt_last_translation": None,
            "tts_audio_url": None,
            "tts_audio_dur": 0,
            "tts_queue": [],
            "_prev_mode": None,
        })
        
        quick_reply = create_quick_reply(MODE_SELECTION_OPTIONS)
        return "請選擇功能：", False, quick_reply
    
    @staticmethod
    def handle_speak_command(session: Dict, user_id: str) -> Tuple[str, bool, Optional[Dict]]:
        """Handle 'speak' command - generate TTS"""
        # Block in Education mode
        if session.get("mode") == "edu":
            quick_reply = create_quick_reply([("🆕 新對話", "new")])
            return (
                "⚠️ 目前在『衛教』模式，無法語音朗讀。\n"
                "若要使用語音功能請點擊下方按鈕：",
                False,
                quick_reply
            )
        
        # Get text to speak
        tts_source = (
            session.get("stt_last_translation") or 
            session.get("translated_output")
        )
        
        if not tts_source:
            return "⚠️ 尚未有可朗讀的翻譯內容。", False, None
        
        # Generate TTS
        try:
            url, duration = synthesize(tts_source, user_id)
            session["tts_audio_url"] = url
            session["tts_audio_dur"] = duration
            session.pop("stt_last_translation", None)  # Clean up
            
            quick_reply = create_quick_reply([("🆕 新對話", "new")])
            return "🔊 語音檔已生成", False, quick_reply
        except Exception as e:
            print(f"[TTS ERROR] {e}")
            return "⚠️ 語音合成失敗，請稍後再試。", False, None


class EducationHandler:
    """Handler for education mode commands"""
    
    @staticmethod
    def handle_modify(session: Dict, text: str) -> Tuple[str, bool, Optional[Dict]]:
        """Handle content modification request"""
        if not session.get("zh_output"):
            return "⚠️ 尚無內容可修改，請先產生衛教內容。", False, None
        
        session["awaiting_modify"] = True
        return "✏️ 請描述您要如何修改內容：", False, None
    
    @staticmethod
    def process_modification(session: Dict, instruction: str) -> Tuple[str, bool, Optional[Dict]]:
        """Process the actual modification"""
        prompt = f"User instruction:\n{instruction}\n\nOriginal content:\n{session['zh_output']}"
        new_content = call_zh(prompt, system_prompt=modify_prompt)
        
        session.update({
            "zh_output": new_content,
            "awaiting_modify": False
        })
        
        # Update references
        new_refs = get_references()
        if new_refs:
            print(f"[MODIFY] Found {len(new_refs)} new references")
        update_session_references(session, new_refs)
        
        quick_reply = create_quick_reply([
            ("✏️ 修改", "modify"),
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])
        
        return "✅ 內容已根據您的要求修改。", True, quick_reply
    
    @staticmethod
    def handle_translate(session: Dict) -> Tuple[str, bool, Optional[Dict]]:
        """Handle translation request"""
        if not session.get("zh_output"):
            return "⚠️ 尚無內容可翻譯，請先產生衛教內容。", False, None
        
        session["awaiting_translate_language"] = True
        quick_reply = create_quick_reply(COMMON_LANGUAGES)
        return "🌐 請選擇要翻譯的語言：", False, quick_reply
    
    @staticmethod
    def process_translation(session: Dict, language: str) -> Tuple[str, bool, Optional[Dict]]:
        """Process the actual translation"""
        # Normalize language
        language = normalize_language_input(language)
        
        # Validate language
        try:
            language = validate_language_code(language)
        except ValueError:
            quick_reply = create_quick_reply(COMMON_LANGUAGES)
            return f"⚠️ 不支援的語言：{language}", False, quick_reply
        
        # Translate
        translated = call_translate(session["zh_output"], language)
        
        session.update({
            "translated_output": translated,
            "translated": True,
            "awaiting_translate_language": False,
            "last_translation_lang": language,
            "last_topic": session["zh_output"].split("\n")[0][:20]
        })
        
        # Update references
        new_refs = get_references()
        update_session_references(session, new_refs)
        
        quick_reply = create_quick_reply([
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])
        
        return f"🌐 翻譯完成（目標語言：{language}）。", True, quick_reply
    
    @staticmethod
    def handle_mail(session: Dict) -> Tuple[str, bool, Optional[Dict]]:
        """Handle email request"""
        if not session.get("zh_output"):
            return "⚠️ 尚無內容可寄送，請先產生衛教內容。", False, None
        
        session["awaiting_email"] = True
        return "📧 請輸入您要寄送至的 email 地址：", False, None
    
    @staticmethod
    def process_email(session: Dict, email: str) -> Tuple[str, bool, Optional[Dict]]:
        """Process email sending"""
        # Validate email
        try:
            validated_email = validate_email(email)
            domain = validated_email.split("@")[1]
            
            if not check_mx_record(domain):
                return f"⚠️ 無法驗證 {domain} 的郵件伺服器，請確認 email 地址正確。", False, None
        
        except ValueError as e:
            return f"⚠️ 無效的 email 地址：{e}", False, None
        
        # Send email
        session["awaiting_email"] = False
        success = send_last_txt_email(validated_email, session)
        
        if success:
            quick_reply = create_quick_reply([("🆕 新對話", "new")])
            return f"✅ 已成功寄出衛教內容至 {validated_email}", False, quick_reply
        else:
            return "⚠️ 寄送失敗，請稍後再試。", False, None


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
    
    Returns:
        (reply_text, gemini_called, quick_reply_data)
    """
    # Clean input
    text = text.strip()
    text_lower = text.lower()
    
    # Initialize response
    gemini_called = False
    quick_reply = None
    
    # ========================================
    # GLOBAL COMMANDS (work in any state)
    # ========================================
    
    # Handle 'new' command
    if text_lower in new_commands:
        return CommandHandler.handle_new_command(session)
    
    # Handle 'speak' command (if session started)
    if session.get("started") and text_lower in speak_commands:
        return CommandHandler.handle_speak_command(session, user_id)
    
    # Handle continue_translate for resuming translation
    if session.get("started") and text_lower == "continue_translate":
        if session.get("mode") == "chat" and session.get("chat_target_lang"):
            lang = session.get("chat_target_lang")
            return f"✅ 語言已設定為「{lang}」，請輸入要翻譯的文字：", False, None
        else:
            return "⚠️ 目前無法繼續翻譯。", False, None
    
    # ========================================
    # UNSTARTED SESSION
    # ========================================
    
    if not session.get("started"):
        quick_reply = create_quick_reply([("🆕 開始", "new")])
        return "請點擊下方按鈕開始：", False, quick_reply
    
    # ========================================
    # MODE SELECTION
    # ========================================
    
    if session.get("mode") is None:
        # STT Translation mode (special case)
        if session.get("awaiting_stt_translation"):
            return _handle_stt_translation(session, text_lower)
        
        # Education mode
        if text_lower in edu_commands:
            session["mode"] = "edu"
            quick_reply = create_quick_reply(COMMON_DISEASES)
            return "📚 進入衛教模式。請輸入要查詢的健康主題：", False, quick_reply
        
        # Chat mode
        if text_lower in chat_commands:
            return _start_chat_mode(session)
        
        # Default prompt
        quick_reply = create_quick_reply(MODE_SELECTION_OPTIONS)
        return "請選擇功能：", False, quick_reply
    
    # ========================================
    # EDUCATION MODE
    # ========================================
    
    if session.get("mode") == "edu":
        return _handle_education_mode(session, text, text_lower)
    
    # ========================================
    # CHAT MODE
    # ========================================
    
    if session.get("mode") == "chat":
        return handle_medchat(user_id, text, session)
    
    # ========================================
    # FALLBACK
    # ========================================
    
    quick_reply = create_quick_reply([
        ("🆕 開始", "new"),
        ("✏️ 修改", "modify"),
        ("🌐 翻譯", "translate")
    ])
    return "⚠️ 無法理解您的指令，請選擇下方按鈕或輸入有效指令。", False, quick_reply


# ============================================================
# MODE HANDLERS
# ============================================================

def _handle_stt_translation(session: Dict, text: str) -> Tuple[str, bool, Optional[Dict]]:
    """Handle STT translation flow"""
    if text == "無":
        session.update({
            "awaiting_stt_translation": False,
            "stt_transcription": None,
            "mode": session.get("_prev_mode", "edu")
        })
        quick_reply = create_quick_reply([("🆕 新對話", "new")])
        return "✅ 已取消語音翻譯。", False, quick_reply
    
    # Process translation
    language = normalize_language_input(text)
    
    try:
        language = validate_language_code(language)
    except ValueError:
        quick_reply = create_quick_reply(COMMON_LANGUAGES + [("❌ 無", "無")])
        return f"⚠️ 不支援的語言。請重新選擇：", False, quick_reply
    
    # Translate
    transcription = session.get("stt_transcription", "")
    prompt = f"原始訊息：\n{transcription}"
    system_prompt = f"You are a medical translation assistant fluent in {language}. Please translate the following message to {language}."
    
    translation = call_zh(prompt, system_prompt=system_prompt)
    
    # Update session
    session.update({
        "stt_last_translation": translation,
        "awaiting_stt_translation": False,
        "mode": session.get("_prev_mode", "edu")
    })
    
    # Log to Drive
    upload_stt_translation_log(
        session.get("user_id", "unknown"),
        transcription,
        translation,
        language
    )
    
    quick_reply = create_quick_reply([
        ("🔊 朗讀", "speak"),
        ("🆕 新對話", "new")
    ])
    
    return f"🌐 翻譯完成（{language}）：\n\n{translation}", True, quick_reply


def _start_chat_mode(session: Dict) -> Tuple[str, bool, Optional[Dict]]:
    """Initialize chat mode"""
    session.update({
        "mode": "chat",
        "awaiting_chat_language": True
    })
    quick_reply = create_quick_reply(COMMON_LANGUAGES)
    return "💬 進入對話模式。請選擇翻譯語言：", False, quick_reply


def _handle_education_mode(
    session: Dict,
    text: str,
    text_lower: str
) -> Tuple[str, bool, Optional[Dict]]:
    """Handle education mode logic"""
    handler = EducationHandler()
    
    # Check for command keywords
    is_modify = text_lower in modify_commands
    is_translate = text_lower in translate_commands
    is_mail = text_lower in mail_commands
    
    # Handle awaiting states
    if session.get("awaiting_modify"):
        return handler.process_modification(session, text)
    
    if session.get("awaiting_translate_language"):
        return handler.process_translation(session, text)
    
    if session.get("awaiting_email"):
        return handler.process_email(session, text)
    
    # Handle commands
    if is_modify:
        return handler.handle_modify(session)
    
    if is_translate:
        return handler.handle_translate(session)
    
    if is_mail:
        return handler.handle_mail(session)
    
    # First-time content generation
    if not session.get("zh_output"):
        zh_content = call_zh(text)
        session.update({
            "zh_output": zh_content,
            "last_topic": text[:30]
        })
        
        # Get references
        new_refs = get_references()
        update_session_references(session, new_refs)
        
        quick_reply = create_quick_reply([
            ("✏️ 修改", "modify"),
            ("🌐 翻譯", "translate"),
            ("📧 寄送", "mail"),
            ("🆕 新對話", "new")
        ])
        
        return "✅ 中文版衛教內容已生成。", True, quick_reply
    
    # Fallback
    quick_reply = create_quick_reply([
        ("🆕 開始", "new"),
        ("✏️ 修改", "modify"),
        ("🌐 翻譯", "translate"),
        ("📧 寄送", "mail")
    ])
    
    existing = []
    if session.get("zh_output"):
        existing.append("中文衛教內容")
    if session.get("translated_output"):
        existing.append(f"{session.get('last_translation_lang', '')}翻譯")
    
    status = f"目前已有：{', '.join(existing)}" if existing else ""
    
    return f"⚠️ 請選擇您要執行的操作。{status}", False, quick_reply