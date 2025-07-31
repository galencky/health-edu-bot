from utils.email_service import send_email
from utils.r2_service import get_r2_service
from datetime import datetime

def send_last_txt_email(user_id: str, to_email: str, session: dict) -> tuple[bool, str]:
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
        content = f"📄 中文衛教內容：\n{zh}{ref_str}\n\n提醒：此內容尚未翻譯。如需多語言版本，請於 LINE 輸入『翻譯』進行語言轉換。"
        subject = f"[Mededbot-多語言衛教AI] 中文 {topic} 衛教單張"

    # Email content prepared successfully
    
    # Upload email content to R2
    r2_url = None
    try:
        r2_service = get_r2_service()
        print(f"📧 [Email] R2 service available: {r2_service is not None}")
        if r2_service:
            # Create timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create email log content with metadata
            email_log_content = f"""Email Log
========================================
Timestamp: {timestamp}
User ID: {user_id}
Recipient: {to_email}
Subject: {subject}
Topic: {topic}
Language: {translated_lang or 'Chinese only'}

Email Content:
========================================
{content}

Metadata:
========================================
Original content length: {len(zh) if zh else 0} characters
Translated content length: {len(translated) if translated else 0} characters
References count: {len(references)}
"""
            
            # Upload to R2 with email indicator in filename
            filename = f"{user_id}-email-{timestamp}.txt"
            print(f"📧 [Email] Uploading file: {filename} to folder: text/{user_id}")
            result = r2_service.upload_text_file(
                email_log_content, 
                filename, 
                folder=f"text/{user_id}"
            )
            print(f"📧 [Email] Upload result: {result}")
            r2_url = result.get('webViewLink')
            print(f"✅ [Email] Content uploaded to R2: {r2_url}")
    except Exception as e:
        print(f"⚠️ [Email] Failed to upload to R2: {e}")
        import traceback
        traceback.print_exc()
        # Continue with email sending even if R2 upload fails
    
    # Send email
    success = send_email(to_email, subject, content)
    
    return success, r2_url
