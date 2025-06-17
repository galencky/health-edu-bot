"""Language normalization utilities"""

def normalize_language_input(text: str) -> str:
    """Normalize language input for better matching"""
    text = text.strip()
    
    # Don't lowercase if it's already in the correct format
    replacements = {
        "台語": "台語",  # Keep as-is for Taigi service
        "臺語": "台語",  # Normalize to 台語
        "taiwanese": "台語",
        "Taiwanese": "台語",
        "taigi": "台語",
        "Taigi": "台語",
        "台灣": "臺灣",
        "中文": "中文(繁體)",
        "english": "英文",
        "English": "英文",
        "japanese": "日文",
        "Japanese": "日文",
        "thai": "泰文",
        "Thai": "泰文",
        "vietnamese": "越南文",
        "Vietnamese": "越南文",
        "indonesian": "印尼文",
        "Indonesian": "印尼文"
    }
    
    # Check exact match first
    if text in replacements:
        return replacements[text]
    
    # Check lowercase match
    text_lower = text.lower()
    for old, new in replacements.items():
        if old.lower() == text_lower:
            return new
    
    # Return original if no match (already could be correct like "日文")
    return text