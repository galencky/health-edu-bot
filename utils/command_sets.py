"""
Centralised lists of recognised command words.
Edit here if you want to add synonyms.
"""

# conversation control
new_commands       = {"new", "開始"}

# mode selection *after* new
edu_commands       = {"ed", "education", "衛教"}
chat_commands      = {"chat", "聊天"}

# education-branch commands
modify_commands    = {"modify", "修改"}
translate_commands = {"translate", "翻譯", "trans"}
mail_commands      = {"mail", "寄送"}
speak_commands = {"speak", "朗讀"}


def create_quick_reply_items(options):
    """
    Create quick reply items for LINE messaging API.
    
    Args:
        options: List of tuples (label, text) or strings (where label=text)
    
    Returns:
        List of quick reply items
    """
    items = []
    for option in options:
        if isinstance(option, tuple):
            label, text = option
        else:
            label = text = option
        
        items.append({
            "type": "action",
            "action": {
                "type": "message",
                "label": label[:20],  # LINE limits label to 20 chars
                "text": text
            }
        })
    return items


# Predefined quick reply sets
MODE_SELECTION_OPTIONS = [
    ("🏥 衛教單張", "衛教"),
    ("💬 醫療翻譯", "chat")
]

COMMON_LANGUAGES = [
    ("🇹🇼 中文(繁體)", "中文(繁體)"),
    ("🇬🇧 英文", "英文"),
    ("🇯🇵 日文", "日文"),
    ("🇰🇷 韓文", "韓文"),
    ("🇹🇭 泰文", "泰文"),
    ("🇻🇳 越南文", "越南文"),
    ("🇮🇩 印尼文", "印尼文"),
    ("🇪🇸 西班牙文", "西班牙文"),
    ("🇫🇷 法文", "法文")
]
# Note: These are just common suggestions - the system supports ALL languages

COMMON_DISEASES = [
    ("糖尿病", "糖尿病"),
    ("高血壓", "高血壓"),
    ("心臟病", "心臟病"),
    ("氣喘", "氣喘"),
    ("過敏", "過敏"),
    ("流感", "流感"),
    ("COVID-19", "COVID-19"),
    ("腎臟病", "腎臟病")
]

TTS_OPTIONS = [
    ("🔊 朗讀", "朗讀"),
    ("🆕 新對話", "new")
]

# Chat mode specific - includes new and continue translate
CHAT_TTS_OPTIONS = [
    ("🔊 朗讀", "朗讀"),
    ("💬 繼續翻譯", "continue_translate"),
    ("🆕 新對話", "new")
]

VOICE_TRANSLATION_OPTIONS = COMMON_LANGUAGES + [("❌ 無", "無")]