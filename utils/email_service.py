
from dotenv import load_dotenv
load_dotenv()   # ← ensure .env is loaded here

import os
import smtplib
from email.message import EmailMessage
from .validators import validate_email, sanitize_text

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Ensure these are set
if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
    raise ValueError("Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in environment variables.")

DISCLAIMER = """您好，

感謝您使用Mededbot-多語言衛教AI的衛教單張生成暨翻譯服務。

以下為免責聲明，請務必留意：
1. 以下內容為大型語言模型根據您的指令所生成，不能代表正式醫療建議，請務必核對內容。
2. 翻譯內容為大型語言模型所翻譯，無法保證翻譯內容完全正確。
3. 若您對翻譯內容有疑慮，建議將翻譯後的內容請可信賴的翻譯服務(如Google Translate, DeepL, 或是ChatGPT)將內容翻譯回您的母語，若出現語意差異，請斟酌使用。

若有任何問題，歡迎來信詢問，煩請各位不吝指教。

陳冠元 醫師 敬上
galen147258369@gmail.com
"""

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email or not subject or not body:
        return False
    
    # Validate and sanitize inputs
    try:
        to_email = validate_email(to_email)
        subject = sanitize_text(subject, max_length=200)
        body = sanitize_text(body, max_length=50000)
    except ValueError as e:
        print(f"❌ Email validation failed: {e}")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(DISCLAIMER + "\n\n" + body)

    try:
        # Use SSL on port 465 (no starttls)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False
