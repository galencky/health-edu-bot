from utils.email_service import send_email

def send_last_txt_email(user_id: str, to_email: str, session: dict) -> bool:
    zh = session.get("zh_output")
    translated = session.get("translated_output")
    translated_lang = session.get("last_translation_lang")
    topic = session.get("last_topic", "未知主題")
    references = session.get("references") or []

    # Debug output removed to reduce log verbosity

    # Compose reference list as plain text (for email)
    ref_str = ""
    if references:
        try:
            ref_str = "\n\n參考來源：\n" + "\n".join([
                f"{i+1}. {ref.get('title','')}: {ref.get('url','')}"
                for i, ref in enumerate(references)
                if isinstance(ref, dict)
            ])
        except Exception as e:
            ref_str = "\n\n參考來源： (format error)\n"

    if not zh:
        return False  # No content at all to send

    # Compose email body
    if translated:
        content = f"📄 原文：\n{zh}\n\n🌐 譯文：\n{translated}{ref_str}"
        subject = f"[Mededbot-多語言衛教AI] {translated_lang or '多語言'} {topic} 衛教單張"
    else:
        content = f"📄 中文衛教內容：\n{zh}{ref_str}\n\n⚠️ 此內容尚未翻譯，如需翻譯請於 LINE 輸入『翻譯』指令。"
        subject = f"[Mededbot-多語言衛教AI] 中文 {topic} 衛教單張"

    # Email content prepared successfully

    return send_email(to_email, subject, content)
