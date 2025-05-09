from datetime import datetime
import os
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from utils.google_drive_service import upload_gemini_log

# Setup Google Sheets
def get_sheet():
    if not os.path.exists("credentials.json"):
        creds_b64 = os.getenv("GOOGLE_CREDS_B64")
        if creds_b64:
            with open("credentials.json", "wb") as f:
                f.write(base64.b64decode(creds_b64))
        else:
            raise ValueError("Missing GOOGLE_CREDS_B64 in environment")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open("ChatbotLogs").sheet1

# Log to sheet
def log_to_sheet(user_id, message, reply, session, action_type=None, gemini_call=None):
    if gemini_call == "yes":
        drive_url, filename = upload_gemini_log(user_id, session, message)
        zh_output = f'=HYPERLINK("{drive_url}", "{filename}")'
        translated_output = zh_output  # hyperlink also shown here
        gemini_call_val = "yes"
    else:
        zh_output = ""
        translated_output = str(session.get("translated_output") or "")[:200]
        gemini_call_val = ""

    row = [
        datetime.now().isoformat(),
        user_id,
        message,
        reply[:200],
        action_type,
        gemini_call_val,
        zh_output,
        translated_output
    ]

    sheet = get_sheet()
    sheet.append_row(row, value_input_option='USER_ENTERED')  # ✅ interprets formulas