# === File: utils/voicemail_drive.py ===

import os
import traceback
from datetime import datetime
from googleapiclient.http import MediaFileUpload
from utils.google_drive_service import get_drive_service

def upload_voicemail_to_drive(local_path: str, user_id: str) -> str:
    """
    Uploads the local audio file at `local_path` to Google Drive under the configured folder.
    Returns the "webViewLink" (or a constructed view URL) on success.
    Raises on failure.
    """

    drive_service = get_drive_service()
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID in environment.")

    # Use a timestamp‐based name to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(local_path)

    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    try:
        media = MediaFileUpload(local_path, mimetype="audio/m4a")
        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
    except Exception as e:
        # Make sure the MediaFileUpload file descriptor is closed
        try:
            if hasattr(media, "_fd") and not media._fd.closed:
                media._fd.close()
        except:
            pass
        raise RuntimeError(f"Failed to upload voicemail to Drive: {e}\n{traceback.format_exc()}")

    # Extract a shareable link; "webViewLink" should give a preview URL
    web_link = uploaded.get("webViewLink")
    if not web_link:
        # Fallback to a generic URL if webViewLink isn't provided
        file_id = uploaded.get("id")
        web_link = f"https://drive.google.com/file/d/{file_id}/view"
    return web_link
