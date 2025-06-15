"""
Async logging module that uses async PostgreSQL for database operations.
Google Drive is still used for file storage, but not for logging.
"""
import os
import asyncio
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils.database import log_chat_to_db, log_tts_to_db
from utils.google_drive_service import get_drive_service, upload_gemini_log as _upload_gemini_log_original
from utils.retry_utils import exponential_backoff, RetryError

# Global thread pool executor to limit thread creation
# This prevents unlimited thread spawning that could cause resource exhaustion
_logging_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="logging-")


async def _async_log_chat(user_id, message, reply, session, action_type=None, gemini_call=None):
    """
    Log chat interaction to database asynchronously.
    If gemini_call is "yes", also uploads detailed log to Drive.
    """
    print(f"🔍 [LOGGING] _async_log_chat called with action_type='{action_type}', gemini_call='{gemini_call}'")
    drive_url = None
    
    if gemini_call == "yes":
        try:
            # Run Drive upload in bounded thread pool since it's sync
            loop = asyncio.get_event_loop()
            drive_url, _ = await loop.run_in_executor(
                _logging_executor, 
                _upload_gemini_log_original, 
                user_id, 
                session, 
                message
            )
        except Exception as e:
            print(f"Failed to upload Gemini log to Drive: {e}")
    
    # Log to database asynchronously
    try:
        db_success = await log_chat_to_db(
            user_id=user_id,
            message=message,
            reply=reply,
            action_type=action_type,
            gemini_call=(gemini_call == "yes"),
            gemini_output_url=drive_url
        )
        if not db_success:
            print(f"⚠️ [LOGGING] Chat log failed to save to database")
            return False
        return True
    except Exception as e:
        print(f"❌ [LOGGING] Database logging failed: {e}")
        return False


async def _log_tts_internal(user_id, text, audio_path, audio_url):
    """
    Internal async function to log TTS generation and upload audio to Drive.
    """
    from utils.storage_config import TTS_USE_MEMORY
    
    web_link = None
    upload_status = "pending"
    retry_count = 0
    
    # Handle Drive upload for both memory and disk storage
    if os.getenv("GOOGLE_DRIVE_FOLDER_ID"):
        # Define upload function with retry decorator
        @exponential_backoff(
            max_retries=3,
            initial_delay=1.0,
            max_delay=30.0,
            exceptions=(Exception,),
            on_retry=lambda attempt, error: print(f"[TTS Upload] Retry {attempt} due to: {error}")
        )
        def upload_to_drive():
            nonlocal retry_count
            retry_count += 1
            
            service = get_drive_service()
            folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
            if not folder_id:
                raise ValueError("GOOGLE_DRIVE_FOLDER_ID not configured")
            
            filename = os.path.basename(audio_path)
            
            # Detect file type and set appropriate mimetype
            if filename.lower().endswith('.wav'):
                mimetype = "audio/wav"
            elif filename.lower().endswith('.m4a'):
                mimetype = "audio/mp4"
            elif filename.lower().endswith('.mp3'):
                mimetype = "audio/mpeg"
            else:
                mimetype = "audio/wav"  # Default fallback
            
            file_metadata = {
                "name": filename,
                "parents": [folder_id]
            }
            
            from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
            media = None
            try:
                # Handle memory storage - get data from memory
                if TTS_USE_MEMORY:
                    from utils.memory_storage import memory_storage
                    import io
                    
                    result = memory_storage.get(filename)
                    if not result:
                        raise FileNotFoundError(f"Audio file not found in memory: {filename}")
                    
                    # Extract audio data from tuple (data, content_type)
                    audio_data, _ = result
                    
                    # Create a BytesIO object for upload
                    audio_buffer = io.BytesIO(audio_data)
                    file_size = len(audio_data)
                    
                # Handle disk storage - check if file exists
                elif not os.path.exists(audio_path):
                    raise FileNotFoundError(f"Audio file not found: {audio_path}")
                else:
                    # Get file size for disk storage
                    file_size = os.path.getsize(audio_path)
                
                print(f"[TTS Upload] File: {filename}, Size: {file_size} bytes, MIME: {mimetype}")
                
                if file_size == 0:
                    raise ValueError(f"Audio file is empty")
                
                # Create media upload
                if TTS_USE_MEMORY:
                    # For memory storage, use MediaIoBaseUpload
                    media = MediaIoBaseUpload(
                        audio_buffer,
                        mimetype=mimetype,
                        resumable=(file_size > 5 * 1024 * 1024)
                    )
                    print(f"[TTS Upload] Using memory upload")
                else:
                    # For disk storage, use MediaFileUpload
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        media = MediaFileUpload(
                            audio_path, 
                            mimetype=mimetype,
                            resumable=True,
                            chunksize=1024*1024  # 1MB chunks for better reliability
                        )
                        print(f"[TTS Upload] Using resumable upload for large file")
                    else:
                        media = MediaFileUpload(
                            audio_path, 
                            mimetype=mimetype,
                            resumable=False
                        )
                        print(f"[TTS Upload] Using simple upload for small file")
                
                # Upload file
                if media._resumable:
                    request = service.files().create(
                        body=file_metadata, 
                        media_body=media, 
                        fields="id,webViewLink"
                    )
                    
                    uploaded = None
                    while uploaded is None:
                        status, uploaded = request.next_chunk()
                        if status:
                            print(f"[TTS Upload] Progress: {int(status.progress() * 100)}%")
                else:
                    # Simple upload for small files
                    uploaded = service.files().create(
                        body=file_metadata, 
                        media_body=media, 
                        fields="id,webViewLink"
                    ).execute()
                
                print(f"[TTS Upload] Upload completed successfully, File ID: {uploaded.get('id')}")
                return uploaded
                
            finally:
                # Ensure file handle is closed
                if media and hasattr(media, '_fd') and media._fd and not media._fd.closed:
                    try:
                        media._fd.close()
                    except Exception as e:
                        print(f"[TTS Upload] Failed to close media file descriptor: {e}")
    
        try:
            # Run sync Drive upload in bounded thread pool
            loop = asyncio.get_event_loop()
            uploaded = await loop.run_in_executor(_logging_executor, upload_to_drive)
            
            file_id = uploaded.get("id")
            web_link = uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
            upload_status = "success"
            
        except RetryError as e:
            print(f"[TTS Upload] Failed after all retries: {e}")
            print(f"[TTS Upload] Last error: {e.last_error}")
            upload_status = f"drive_upload_failed_after_{retry_count}_attempts"
            
        except Exception as e:
            print(f"[TTS Upload] Unexpected error: {e}\n{traceback.format_exc()}")
            upload_status = "drive_upload_error"
    
    # Always log to database, even if upload failed
    try:
        db_success = await log_tts_to_db(
            user_id=user_id,
            text=text,
            audio_filename=os.path.basename(audio_path),
            audio_url=audio_url,
            drive_link=web_link,
            status=upload_status
        )
        if not db_success:
            print(f"⚠️ [TTS] Database logging failed but no exception thrown")
    except Exception as db_error:
        print(f"❌ [TTS] Failed to log to database: {db_error}")
    
    # Delete local file after successful Drive upload ONLY if using memory storage
    # If using local storage, we need to keep the files to serve them!
    from utils.storage_config import TTS_USE_MEMORY
    
    if web_link and upload_status == "success" and TTS_USE_MEMORY:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"🗑️ [TTS] Deleted local file after Drive upload (memory storage mode): {os.path.basename(audio_path)}")
        except Exception as e:
            print(f"⚠️ [TTS] Failed to delete local file: {e}")
    elif web_link and upload_status == "success":
        print(f"📁 [TTS] Keeping local file for serving (local storage mode): {os.path.basename(audio_path)}")


async def _async_upload_voicemail(local_path: str, user_id: str, transcription: str = None, translation: str = None) -> str:
    """
    Upload voicemail to Drive and log to database with retry logic.
    Returns the Drive link.
    """
    @exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exceptions=(Exception,),
        on_retry=lambda attempt, error: print(f"[Voicemail Upload] Retry {attempt} due to: {error}")
    )
    def upload_with_retry():
        drive_service = get_drive_service()
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID in environment.")
        
        # Check if file exists
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Voicemail file not found: {local_path}")
        
        filename = os.path.basename(local_path)
        
        # Detect file type and set appropriate mimetype
        if filename.lower().endswith('.m4a'):
            mimetype = "audio/mp4"
        elif filename.lower().endswith('.wav'):
            mimetype = "audio/wav"
        elif filename.lower().endswith('.mp3'):
            mimetype = "audio/mpeg"
        elif filename.lower().endswith('.aac'):
            mimetype = "audio/aac"
        else:
            mimetype = "audio/mp4"  # Default for voicemail (usually m4a)
        
        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }
        
        from googleapiclient.http import MediaFileUpload
        media = None
        try:
            # Check file size
            file_size = os.path.getsize(local_path)
            print(f"[Voicemail Upload] File: {filename}, Size: {file_size} bytes, MIME: {mimetype}")
            
            if file_size == 0:
                raise ValueError(f"Voicemail file is empty: {local_path}")
            
            # Create media upload - use resumable for files > 5MB, otherwise simple upload
            if file_size > 5 * 1024 * 1024:  # 5MB
                media = MediaFileUpload(
                    local_path, 
                    mimetype=mimetype,
                    resumable=True,
                    chunksize=1024*1024  # 1MB chunks for better reliability
                )
                print(f"[Voicemail Upload] Using resumable upload for large file")
            else:
                media = MediaFileUpload(
                    local_path, 
                    mimetype=mimetype,
                    resumable=False
                )
                print(f"[Voicemail Upload] Using simple upload for small file")
            
            # Upload file
            if media._resumable:
                request = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,webViewLink"
                )
                
                uploaded = None
                while uploaded is None:
                    status, uploaded = request.next_chunk()
                    if status:
                        print(f"[Voicemail Upload] Progress: {int(status.progress() * 100)}%")
            else:
                # Simple upload for small files
                uploaded = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,webViewLink"
                ).execute()
            
            print(f"[Voicemail Upload] Upload completed successfully, File ID: {uploaded.get('id')}")
            return uploaded
            
        finally:
            # Ensure file handle is closed
            if media and hasattr(media, "_fd") and media._fd and not media._fd.closed:
                try:
                    media._fd.close()
                except Exception as e:
                    print(f"[Voicemail Upload] Failed to close media file descriptor: {e}")
    
    try:
        # Run sync Drive upload in bounded thread pool
        loop = asyncio.get_event_loop()
        uploaded = await loop.run_in_executor(_logging_executor, upload_with_retry)
        
        # Get Drive link
        web_link = uploaded.get("webViewLink")
        if not web_link:
            file_id = uploaded.get("id")
            web_link = f"https://drive.google.com/file/d/{file_id}/view"
        
        # Skip voicemail_logs table - we only log to chat_logs now
        
        # Delete local file after successful Drive upload
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"🗑️ [Voicemail] Deleted local file after Drive upload: {os.path.basename(local_path)}")
        except Exception as e:
            print(f"⚠️ [Voicemail] Failed to delete local file: {e}")
        
        return web_link
        
    except RetryError as e:
        # All retries exhausted
        error_msg = f"Failed to upload voicemail after all retries: {e.last_error}"
        print(f"[Voicemail Upload] {error_msg}")
        
        # Skip voicemail_logs table - we only log to chat_logs now
        
        raise RuntimeError(error_msg) from e


# Synchronous wrappers for backward compatibility
def log_chat_sync(user_id, message, reply, session, action_type=None, gemini_call=None):
    """
    Synchronous wrapper for log_chat for use in sync contexts.
    Creates a new event loop in a thread to avoid blocking.
    """
    print(f"🔍 [LOGGING] log_chat_sync called with action_type='{action_type}', gemini_call='{gemini_call}'")
    
    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print(f"🔄 [LOGGING] Starting async chat log for user {user_id[:10]}...")
            success = loop.run_until_complete(_async_log_chat(user_id, message, reply, session, action_type, gemini_call))
            if success:
                print(f"✅ [LOGGING] Chat logging completed successfully")
            else:
                print(f"❌ [LOGGING] Chat logging failed")
        except Exception as e:
            print(f"❌ [LOGGING] Chat logging thread failed: {e}")
        finally:
            loop.close()
    
    # Use bounded thread pool executor instead of unlimited threading
    _logging_executor.submit(_worker)


def log_tts_async(user_id, text, audio_path, audio_url):
    """
    Fire-and-forget async logging for TTS generation with Drive upload.
    Creates a new event loop in a thread to handle the async operations.
    """
    print(f"🔍 [TTS LOG] Starting TTS logging for user {user_id[:10]}..., file: {os.path.basename(audio_path) if '/' in str(audio_path) else audio_path}")
    
    def _worker():
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print(f"🔄 [TTS] Starting TTS logging and Drive upload for user {user_id[:10]}...")
            loop.run_until_complete(_log_tts_internal(user_id, text, audio_path, audio_url))
            print(f"✅ [TTS] TTS logging thread completed")
        except Exception as e:
            print(f"❌ [TTS] TTS logging thread failed: {e}")
        finally:
            loop.close()
    
    # Use bounded thread pool executor instead of unlimited threading
    _logging_executor.submit(_worker)


def upload_voicemail_sync(local_path: str, user_id: str, transcription: str = None, translation: str = None) -> str:
    """
    Synchronous wrapper for upload_voicemail.
    Blocks until upload is complete.
    """
    # Try to get current event loop
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, can't use run_until_complete
        # Create a new thread with its own event loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                _async_upload_voicemail(local_path, user_id, transcription, translation)
            )
            return future.result()
    except RuntimeError:
        # No event loop, we can create one
        return asyncio.run(_async_upload_voicemail(local_path, user_id, transcription, translation))


# Smart wrappers that detect context and call appropriate version
def log_chat(*args, **kwargs):
    """
    Smart wrapper that detects if we're in async context.
    If async, returns coroutine. If sync, runs in thread.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're in async context - but we need to check if we're actually in a coroutine
        # For now, just use sync version to avoid issues
        log_chat_sync(*args, **kwargs)
    except RuntimeError:
        # We're in sync context, use the sync wrapper
        log_chat_sync(*args, **kwargs)


def upload_voicemail(*args, **kwargs):
    """
    Smart wrapper that detects if we're in async context.
    If async, returns coroutine. If sync, blocks until complete.
    """
    try:
        asyncio.get_running_loop()
        # We're in async context, return the coroutine
        return _async_upload_voicemail(*args, **kwargs)
    except RuntimeError:
        # We're in sync context, use the sync wrapper
        return upload_voicemail_sync(*args, **kwargs)