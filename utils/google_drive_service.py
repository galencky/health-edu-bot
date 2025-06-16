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

def _upload_text_file(filename: str, content: str, log_type: str):
    """Unified text file upload logic"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        @exponential_backoff(
            max_retries=3,
            initial_delay=0.5,
            max_delay=15.0,
            exceptions=(Exception,),
            on_retry=lambda attempt, error: print(f"[{log_type}] Retry {attempt} due to: {error}")
        )
        def upload_with_retry():
            drive_service = get_drive_service()
            file_metadata = {"name": filename, "parents": [DRIVE_FOLDER_ID]}
            
            media = MediaFileUpload(
                filename, 
                mimetype="text/plain",
                resumable=True,
                chunksize=256*1024
            )
            
            try:
                request = drive_service.files().create(
                    body=file_metadata, 
                    media_body=media, 
                    fields="id"
                )
                
                uploaded = None
                while uploaded is None:
                    status, uploaded = request.next_chunk()
                
                return uploaded
                
            finally:
                if media and hasattr(media, '_fd') and media._fd and not media._fd.closed:
                    try:
                        media._fd.close()
                    except Exception as e:
                        print(f"[{log_type}] Failed to close media file descriptor: {e}")
        
        try:
            uploaded_file = upload_with_retry()
            file_id = uploaded_file["id"]
            return f"https://drive.google.com/file/d/{file_id}/view", filename
            
        except RetryError as e:
            print(f"[{log_type}] Failed after all retries: {e}")
            return None, filename
    
    finally:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {filename}: {e}")


def upload_gemini_log(user_id, session, message):
    """Upload .txt Gemini log to Google Drive with retry logic"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}-{timestamp}.txt"
    
    # Build content based on what's available in session
    content_parts = [f"Timestamp: {timestamp}", f"User ID: {user_id}", f"Input Message: {message}", ""]
    
    # Add all relevant session outputs
    session_fields = {
        'zh_output': 'Gemini zh_output:',
        'translated_output': 'Gemini translated_output:',
        'chinese_output': 'Gemini chinese_output (MedChat):',
        'translation_output': 'Gemini translation_output (MedChat):',
        'stt_last_translation': 'STT Translation:',
        'last_gemini_response': 'Last Gemini Response:'
    }
    
    for field, label in session_fields.items():
        if session.get(field):
            content_parts.extend([label, session.get(field), ""])
    
    content = "\n".join(content_parts)
    return _upload_text_file(filename, content, "Gemini Log Upload")

def upload_stt_translation_log(user_id, transcription, translation, target_language):
    """Upload STT translation log to Google Drive"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}-stt-translation-{timestamp}.txt"
    content = (
        f"Timestamp: {timestamp}\n"
        f"User ID: {user_id}\n"
        f"Target Language: {target_language}\n\n"
        f"Original Transcription:\n{transcription}\n\n"
        f"Translation:\n{translation}\n"
    )
    
    url, _ = _upload_text_file(filename, content, "STT Translation Upload")
    if url:
        print(f"✅ [STT Translation] Uploaded text log to Drive: {filename}")
    return url, filename

