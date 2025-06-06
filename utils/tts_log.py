# === File: utils/tts_log.py ===
import threading
import os
import traceback
from datetime import datetime
from utils.google_drive_service import get_drive_service
from utils.google_sheets import get_gspread_client

def log_tts_to_drive_and_sheet(user_id, text, audio_path, audio_url):
    def _worker():
        try:
            # --- Upload audio to Google Drive ---
            service = get_drive_service()
            folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
            filename = os.path.basename(audio_path)
            file_metadata = {
                "name": filename,
                "parents": [folder_id]
            }
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(audio_path, mimetype="audio/wav")
            uploaded = service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
            file_id = uploaded.get("id")
            web_link = uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"

            # --- Log to Google Sheets ---
            client = get_gspread_client()
            try:
                sheet = client.open("ChatbotLogs").worksheet("TTSLogs")
            except Exception:
                # If worksheet doesn't exist, create it.
                sheet = client.open("ChatbotLogs").add_worksheet(title="TTSLogs", rows="1000", cols="7")
                sheet.append_row(["Timestamp", "UserID", "Text", "Audio File", "Audio URL", "Drive Link", "Status"])

            row = [
                datetime.now().isoformat(),
                user_id,
                text[:200],
                filename,
                audio_url,
                web_link,
                "success"
            ]
            sheet.append_row(row)
        except Exception as e:
            print(f"[TTS LOG ERROR] {e}\n{traceback.format_exc()}")
    threading.Thread(target=_worker, daemon=True).start()
