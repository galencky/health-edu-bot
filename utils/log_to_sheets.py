from datetime import datetime
from utils.google_sheets import get_gspread_client

# You can cache the sheet to avoid reopening it on every call
_gspread_client = get_gspread_client()
_sheet = _gspread_client.open("ChatbotLogs").sheet1  # Update sheet name as needed

def log_to_sheet(user_id, message, reply, session, action_type=None, gemini_call=None):
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

    _sheet.append_row(row)
