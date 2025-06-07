from datetime import datetime
import os
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from utils.google_drive_service import upload_gemini_log
from utils.paths import CREDS_PATH

# Setup Google Sheets
def get_sheet():
    if not os.path.exists(str(CREDS_PATH)):
        creds_b64 = os.getenv("GOOGLE_CREDS_B64")
        if creds_b64:
            with open(str(CREDS_PATH), "wb") as f:
                f.write(base64.b64decode(creds_b64))
        else:
            raise ValueError("Missing GOOGLE_CREDS_B64 in environment")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDS_PATH), scope)
    client = gspread.authorize(creds)
    return client.open("ChatbotLogs").sheet1

# Log to sheet
def log_to_sheet(user_id, message, reply, session, action_type=None, gemini_call=None):
    if gemini_call == "yes":
        drive_url, filename = upload_gemini_log(user_id, session, message)
        gemini_output = f'=HYPERLINK("{drive_url}", "{filename}")'
        gemini_call_val = "yes"
    else:
        gemini_output = ""
        gemini_call_val = ""

    row = [
        datetime.now().isoformat(),
        user_id,
        message,
        reply[:200],
        action_type,
        gemini_call_val,
        gemini_output  # ✅ now a single unified output column
    ]

    sheet = get_sheet()
    sheet.append_row(row, value_input_option='USER_ENTERED')
