import os
from utils.email_service import send_email

def send_last_txt_email(user_id: str, to_email: str, session: dict) -> bool:
    zh = session.get("zh_output")
    translated = session.get("translated_output")
    if not zh or not translated:
        return False  # fallback if Gemini output not available

    # Compose email content from in-memory Gemini results
    content = f"📄 原文：\n{zh}\n\n🌐 譯文：\n{translated}"

    # Subject line: e.g. [Mededbot-多語言衛教AI] 日文 糖尿病飲食 衛教單張
    translated_lang = session.get("last_translation_lang", "未知語言")
    topic = session.get("last_topic", "未知主題")
    subject = f"[Mededbot-多語言衛教AI] {translated_lang} {topic} 衛教單張"

    return send_email(to_email, subject, content)