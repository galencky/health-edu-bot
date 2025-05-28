# C:\Users\galen\Downloads\Mededbot\smtp_test.py

import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

# Load and validate environment variables
email = os.getenv("GMAIL_ADDRESS")
password = os.getenv("GMAIL_APP_PASSWORD")

print("Email:", email)

if not email or not password:
    raise ValueError("❌ Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in environment variables.")

try:
    server = smtplib.SMTP("smtp.gmail.com", 465)
    server.starttls()
    server.login(email, password)
    print("✅ Email login succeeded!")
except Exception as e:
    print(f"❌ Email login failed: {e}")
