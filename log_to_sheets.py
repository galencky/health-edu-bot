import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import base64

# ── Decode credentials.json from base64 environment variable ────────────────
if not os.path.exists("credentials.json"):
    creds_b64 = os.getenv("GOOGLE_CREDS_B64")
    if creds_b64:
        with open("credentials.json", "wb") as f:
            f.write(base64.b64decode(creds_b64))
    else:
        raise ValueError("GOOGLE_CREDS_B64 not found in environment.")

# ── Setup Google Sheets API connection ──────────────────────────────────────
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open("ChatbotLogs").sheet1  # Make sure this name matches your sheet

# ── Append a row of interaction log ─────────────────────────────────────────
def log_to_sheet(user_id, message, reply, session, action_type=None, gemini_call=None):
    # Conditionally log zh_output and gemini_call only if Gemini was used
    if gemini_call == "no":
        zh_output = ""
        gemini_call_val = ""
    else:
        zh_output = str(session.get("zh_output") or "")[:200]
        gemini_call_val = gemini_call

    translated_output = str(session.get("translated_output") or "")[:200]

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
    sheet.append_row(row)
