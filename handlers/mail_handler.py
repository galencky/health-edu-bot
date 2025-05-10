import os
from utils.email_service import send_email

def send_last_txt_email(user_id: str, to_email: str, session: dict) -> bool:
    zh = session.get("zh_output")
    translated = session.get("translated_output")
    translated_lang = session.get("last_translation_lang")
    topic = session.get("last_topic", "未知主題")

    if not zh:
        return False  # No content at all to send

    # Compose email body
    if translated:
        content = f"📄 原文：\n{zh}\n\n🌐 譯文：\n{translated}"
        subject = f"[Mededbot-多語言衛教AI] {translated_lang or '多語言'} {topic} 衛教單張"
    else:
        content = f"📄 中文衛教內容：\n{zh}\n\n⚠️ 此內容尚未翻譯，如需翻譯請於 LINE 輸入『翻譯』指令。"
        subject = f"[Mededbot-多語言衛教AI] 中文 {topic} 衛教單張"

    return send_email(to_email, subject, content)
