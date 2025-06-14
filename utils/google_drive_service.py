from dotenv import load_dotenv
load_dotenv()

import os
import base64
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from utils.paths import CREDS_PATH
from utils.retry_utils import exponential_backoff, RetryError

DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
if not DRIVE_FOLDER_ID:
    raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID in environment.")

# BUG FIX: Cache service to avoid repeated credential file writes
# Previously: Credentials written to disk on every API call
_drive_service_cache = None

# Setup Google Drive client with enhanced connection handling
def get_drive_service():
    global _drive_service_cache
    
    if _drive_service_cache is not None:
        return _drive_service_cache
    
    if not os.path.exists(str(CREDS_PATH)):
        creds_b64 = os.getenv("GOOGLE_CREDS_B64")
        if creds_b64:
            with open(str(CREDS_PATH), "wb") as f:
                f.write(base64.b64decode(creds_b64))
        else:
            raise ValueError("Missing GOOGLE_CREDS_B64 environment variable")

    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=["https://www.googleapis.com/auth/drive"])
    
    # Build service with credentials only (http and credentials are mutually exclusive)
    _drive_service_cache = build("drive", "v3", credentials=creds)
    return _drive_service_cache

# Upload .txt Gemini log to Google Drive with retry logic
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

    # Write content to temporary file
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        @exponential_backoff(
            max_retries=3,
            initial_delay=0.5,
            max_delay=15.0,
            exceptions=(Exception,),
            on_retry=lambda attempt, error: print(f"[Gemini Log Upload] Retry {attempt} due to: {error}")
        )
        def upload_with_retry():
            drive_service = get_drive_service()
            file_metadata = {
                "name": filename,
                "parents": [DRIVE_FOLDER_ID]
            }
            
            media = None
            try:
                # Create media upload with resumable=True for better reliability
                media = MediaFileUpload(
                    filename, 
                    mimetype="text/plain",
                    resumable=True,
                    chunksize=256*1024  # 256KB chunks (small for text files)
                )
                
                # Upload with resumable support
                request = drive_service.files().create(
                    body=file_metadata, 
                    media_body=media, 
                    fields="id"
                )
                
                uploaded = None
                while uploaded is None:
                    status, uploaded = request.next_chunk()
                    # Text files are small, so progress tracking isn't needed
                
                return uploaded
                
            finally:
                # Ensure media file handle is closed
                if media and hasattr(media, '_fd') and media._fd and not media._fd.closed:
                    try:
                        media._fd.close()
                    except Exception as e:
                        print(f"[GEMINI LOG] Failed to close media file descriptor: {e}")
        
        try:
            # Upload with retry
            uploaded_file = upload_with_retry()
            file_id = uploaded_file["id"]
            return f"https://drive.google.com/file/d/{file_id}/view", filename
            
        except RetryError as e:
            print(f"[Gemini Log Upload] Failed after all retries: {e}")
            # Return None values to indicate failure
            return None, filename
    
    finally:
        # Always clean up temporary file
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {filename}: {e}")

