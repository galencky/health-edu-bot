"""
Async logging module that uses async PostgreSQL for database operations.
Cloudflare R2 is used for file storage instead of Google Drive.
"""
import os
import asyncio
import traceback
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils.database import log_chat_to_db, log_tts_to_db
from utils.r2_service import upload_gemini_log as _upload_gemini_log_r2, get_r2_service
from utils.retry_utils import exponential_backoff, RetryError

# Global thread pool executor to limit thread creation
# This prevents unlimited thread spawning that could cause resource exhaustion
_logging_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="logging-")


async def _async_log_chat(user_id, message, reply, session, action_type=None, gemini_call=None, gemini_output_url=None):
    """
    Log chat interaction to database asynchronously.
    If gemini_call is "yes", also uploads detailed log to Drive.
    """
    print(f"🔍 [LOGGING] _async_log_chat called with action_type='{action_type}', gemini_call='{gemini_call}'")
    drive_url = gemini_output_url  # Use provided URL if available
    
    # Log language choice if present
    language = session.get("last_translation_lang") or session.get("chat_target_lang")
    if language:
        print(f"🌍 [LOGGING] Language choice: {language}")
    
    # Only upload to R2 if no URL was provided
    if not drive_url and (gemini_call == "yes" or (language and language in ["台語", "臺語", "taiwanese", "taigi"])):
        try:
            # Run R2 upload in bounded thread pool since it's sync
            loop = asyncio.get_event_loop()
            drive_url, _ = await loop.run_in_executor(
                _logging_executor, 
                _upload_gemini_log_r2, 
                user_id, 
                session, 
                message
            )
        except Exception as e:
            print(f"Failed to upload Gemini log to R2: {e}")
    
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
    Internal async function to log TTS generation and upload audio to R2.
    """
    from utils.storage_config import TTS_USE_MEMORY
    
    web_link = None
    upload_status = "pending"
    retry_count = 0
    
    # Handle R2 upload for both memory and disk storage
    if os.getenv("R2_ENDPOINT_URL"):
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
            return _upload_audio_file(audio_path, "TTS Upload")
    
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


def _upload_audio_file(audio_path: str, log_prefix: str = "Audio Upload"):
    """Unified audio file upload logic for both TTS and voicemail"""
    from utils.storage_config import TTS_USE_MEMORY
    
    service = get_r2_service()
    if not service:
        raise ValueError("R2 service not configured")
    
    filename = os.path.basename(audio_path)
    
    # Log Taigi files specifically
    if "_taigi_" in filename:
        print(f"🇹🇼 [{log_prefix}] Uploading Taigi audio file: {filename}")
    
    # Get user_id from filename (format: U{user_id}_{rest})
    user_id = filename.split('_')[0] if '_' in filename else 'unknown'
    
    # Handle memory vs disk storage
    if TTS_USE_MEMORY and log_prefix == "TTS Upload":
        from utils.memory_storage import memory_storage
        import io
        
        # Debug: log memory storage state for Taigi files
        if "_taigi_" in filename:
            print(f"🔍 [TAIGI Upload] Looking for {filename} in memory storage")
            print(f"🔍 [TAIGI Upload] Memory storage keys: {list(memory_storage.files.keys())}")
        
        result = memory_storage.get(filename)
        if not result:
            raise FileNotFoundError(f"Audio file not found in memory: {filename}")
        
        audio_data, _ = result
        file_size = len(audio_data)
        if file_size == 0:
            raise ValueError("Audio file is empty")
    else:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise ValueError(f"Audio file is empty: {audio_path}")
        
        # Read file data
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
    
    print(f"[{log_prefix}] File: {filename}, Size: {file_size} bytes")
    
    # Determine folder based on prefix
    if log_prefix == "TTS Upload":
        folder = f"tts_audio/{user_id}"
    elif log_prefix == "Voicemail Upload":
        folder = f"voicemail/{user_id}"
    else:
        folder = f"audio/{user_id}"
    
    # Upload to R2
    try:
        result = service.upload_audio_file(audio_data, filename, folder=folder)
        print(f"[{log_prefix}] Upload completed successfully, URL: {result.get('webViewLink')}")
        return result
        
    except Exception as e:
        print(f"[{log_prefix}] Upload failed: {e}")
        raise


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
        return _upload_audio_file(local_path, "Voicemail Upload")
    
    try:
        # Run sync Drive upload in bounded thread pool
        loop = asyncio.get_event_loop()
        uploaded = await loop.run_in_executor(_logging_executor, upload_with_retry)
        
        # Get Drive link
        web_link = uploaded.get("webViewLink")
        if not web_link:
            file_id = uploaded.get("id")
            web_link = f"https://drive.google.com/file/d/{file_id}/view"
        
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
        raise RuntimeError(error_msg) from e




# Synchronous wrappers for backward compatibility
def log_chat_sync(user_id, message, reply, session, action_type=None, gemini_call=None, gemini_output_url=None):
    """
    Synchronous wrapper for log_chat for use in sync contexts.
    Handles both cases: with and without existing event loop.
    """
    print(f"🔍 [LOGGING] log_chat_sync called with action_type='{action_type}', gemini_call='{gemini_call}'")
    
    def _worker():
        try:
            print(f"🔄 [LOGGING] Starting async chat log for user {user_id[:10]}...")
            # Try to get existing event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're here, we're in an async context but called from sync code
                # This shouldn't happen with our current fix, but handle it anyway
                print(f"⚠️ [LOGGING] Unexpected: sync function called with active event loop")
                # Create task in existing loop
                future = asyncio.run_coroutine_threadsafe(
                    _async_log_chat(user_id, message, reply, session, action_type, gemini_call, gemini_output_url),
                    loop
                )
                success = future.result(timeout=30)
            except RuntimeError:
                # No event loop, create one
                success = asyncio.run(_async_log_chat(user_id, message, reply, session, action_type, gemini_call, gemini_output_url))
            
            if success:
                print(f"✅ [LOGGING] Chat logging completed successfully")
            else:
                print(f"❌ [LOGGING] Chat logging failed")
        except Exception as e:
            print(f"❌ [LOGGING] Chat logging thread failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Use bounded thread pool executor instead of unlimited threading
    _logging_executor.submit(_worker)


def log_tts_async(user_id, text, audio_path, audio_url):
    """
    Fire-and-forget async logging for TTS generation with Drive upload.
    Handles both cases: with and without existing event loop.
    """
    print(f"🔍 [TTS LOG] Starting TTS logging for user {user_id[:10]}..., file: {os.path.basename(audio_path) if '/' in str(audio_path) else audio_path}")
    
    def _worker():
        try:
            print(f"🔄 [TTS] Starting TTS logging and Drive upload for user {user_id[:10]}...")
            # Try to get existing event loop
            try:
                loop = asyncio.get_running_loop()
                print(f"⚠️ [TTS] Unexpected: sync function called with active event loop")
                # Create task in existing loop
                future = asyncio.run_coroutine_threadsafe(
                    _log_tts_internal(user_id, text, audio_path, audio_url),
                    loop
                )
                future.result(timeout=30)
            except RuntimeError:
                # No event loop, create one
                asyncio.run(_log_tts_internal(user_id, text, audio_path, audio_url))
            print(f"✅ [TTS] TTS logging thread completed")
        except Exception as e:
            print(f"❌ [TTS] TTS logging thread failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Use bounded thread pool executor instead of unlimited threading
    _logging_executor.submit(_worker)


def upload_voicemail_sync(local_path: str, user_id: str, transcription: str = None, translation: str = None) -> str:
    """
    Synchronous wrapper for upload_voicemail.
    Blocks until upload is complete.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, use run_coroutine_threadsafe
        future = asyncio.run_coroutine_threadsafe(
            _async_upload_voicemail(local_path, user_id, transcription, translation),
            loop
        )
        return future.result(timeout=60)  # 60 second timeout for uploads
    except RuntimeError:
        # No event loop, we can create one
        return asyncio.run(_async_upload_voicemail(local_path, user_id, transcription, translation))




# Smart wrappers that detect context and call appropriate version
def log_chat(user_id, message, reply, session, action_type=None, gemini_call=None, gemini_output_url=None):
    """
    Smart wrapper that detects if we're in async context.
    If async, creates a task. If sync, runs in thread.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're in async context, create a task to run the coroutine
        task = loop.create_task(_async_log_chat(user_id, message, reply, session, action_type, gemini_call, gemini_output_url))
        # Add error handler to catch exceptions
        def _handle_task_error(task):
            try:
                task.result()
            except Exception as e:
                print(f"❌ [LOGGING] Async task failed: {e}")
        task.add_done_callback(_handle_task_error)
    except RuntimeError:
        # We're in sync context, use the sync wrapper
        log_chat_sync(user_id, message, reply, session, action_type, gemini_call, gemini_output_url)


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