from dotenv import load_dotenv
load_dotenv()

import os
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from utils.paths import CREDS_PATH

DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
if not DRIVE_FOLDER_ID:
    raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID in environment.")

# Setup Google Drive client
def get_drive_service():
    if not os.path.exists(str(CREDS_PATH)):
        creds_b64 = os.getenv("GOOGLE_CREDS_B64")
        if creds_b64:
            with open(str(CREDS_PATH), "wb") as f:
                f.write(base64.b64decode(creds_b64))
        else:
            raise ValueError("Missing GOOGLE_CREDS_B64 environment variable")

    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)

# Upload .txt Gemini log to Google Drive
def upload_gemini_log(user_id, session, message):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}-{timestamp}.txt"
    content = (
        f"Timestamp: {timestamp}\n"
        f"User ID: {user_id}\n"
        f"Input Message: {message}\n\n"
        f"Gemini zh_output:\n{session.get('zh_output')}\n\n"
        f"Gemini translated_output:\n{session.get('translated_output')}\n"
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    drive_service = get_drive_service()
    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(filename, mimetype="text/plain")
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

    # ---- FIX: Ensure file is closed before deleting ----
    if hasattr(media, '_fd') and not media._fd.closed:
        media._fd.close()

    os.remove(filename)

    file_id = uploaded_file["id"]
    return f"https://drive.google.com/file/d/{file_id}/view", filename

