import os
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_gspread_client():
    if not os.path.exists("credentials.json"):
        creds_b64 = os.getenv("GOOGLE_CREDS_B64")
        if creds_b64:
            with open("credentials.json", "wb") as f:
                f.write(base64.b64decode(creds_b64))
        else:
            raise ValueError("GOOGLE_CREDS_B64 not found in environment.")

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    return gspread.authorize(creds)
