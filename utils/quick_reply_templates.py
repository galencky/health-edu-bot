"""
Quick Reply Templates - Centralized quick reply patterns for consistent UI
"""
from typing import List, Tuple, Dict
from utils.command_sets import create_quick_reply_items, COMMON_LANGUAGES, EDU_LANGUAGES


class QuickReplyTemplates:
    """Centralized quick reply templates for consistent UI"""
    
    # Single action templates
    START = [("🆕 開始", "new")]
    NEW_CONVERSATION = [("🆕 新對話", "new")]
    
    # Education mode actions
    EDU_ACTIONS = [
        ("✏️ 修改", "modify"),
        ("🌐 翻譯", "translate"),
        ("📧 寄送", "mail"),
        ("🆕 新對話", "new")
    ]
    
    EDU_ACTIONS_NO_MODIFY = [
        ("🌐 翻譯", "translate"),
        ("📧 寄送", "mail"),
        ("🆕 新對話", "new")
    ]
    
    EDU_ACTIONS_NO_TRANSLATE = [
        ("📧 寄送", "mail"),
        ("🆕 新對話", "new")
    ]
    
    # Chat mode continue options
    CHAT_CONTINUE = [
        ("🔊 朗讀", "speak"),
        ("🆕 新對話", "new")
    ]
    
    @classmethod
    def create(cls, template_name: str) -> Dict:
        """Create quick reply from predefined template"""
        template = getattr(cls, template_name, cls.START)
        return {"items": create_quick_reply_items(template)}
    
    @classmethod
    def create_custom(cls, options: List[Tuple[str, str]]) -> Dict:
        """Create custom quick reply from provided options"""
        return {"items": create_quick_reply_items(options)}
    
    @classmethod
    def create_languages(cls, language_set: str = "COMMON") -> Dict:
        """Create language selection quick reply"""
        if language_set == "EDU":
            return {"items": create_quick_reply_items(EDU_LANGUAGES)}
        else:
            return {"items": create_quick_reply_items(COMMON_LANGUAGES)}