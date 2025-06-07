import os
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from utils.paths import CREDS_PATH

def get_gspread_client():
    if not os.path.exists(str(CREDS_PATH)):
        creds_b64 = os.getenv("GOOGLE_CREDS_B64")
        if creds_b64:
            with open(str(CREDS_PATH), "wb") as f:
                f.write(base64.b64decode(creds_b64))
        else:
            raise ValueError("GOOGLE_CREDS_B64 not found in environment.")

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(CREDS_PATH), scope)
    return gspread.authorize(creds)
