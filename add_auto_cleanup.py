#!/usr/bin/env python3
"""
Optional enhancement: Add automatic file cleanup after successful Google Drive uploads
This script shows the modifications needed to enable auto-cleanup.
"""

# === OPTION 1: Immediate Cleanup After Upload ===

# Add this to utils/logging.py in the TTS upload success section:
"""
    try:
        # Run sync Drive upload in thread pool
        loop = asyncio.get_event_loop()
        uploaded = await loop.run_in_executor(None, upload_to_drive)
        
        file_id = uploaded.get("id")
        web_link = uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
        upload_status = "success"
        
        # NEW: Auto-cleanup after successful upload
        if os.getenv("AUTO_CLEANUP_FILES", "false").lower() == "true":
            try:
                os.remove(audio_path)
                print(f"🗑️ [TTS Cleanup] Removed local file: {os.path.basename(audio_path)}")
            except Exception as e:
                print(f"⚠️ [TTS Cleanup] Failed to remove file: {e}")
        
    except RetryError as e:
        # Upload failed, keep local file
        print(f"[TTS Upload] Failed after all retries: {e}")
"""

# === OPTION 2: Delayed Cleanup (Keep files for X hours) ===

# Add this new function to utils/logging.py:
"""
import time
from datetime import datetime, timedelta

async def cleanup_old_files():
    '''Clean up files older than specified hours'''
    cleanup_hours = int(os.getenv("CLEANUP_AFTER_HOURS", "24"))  # Default 24 hours
    cutoff_time = time.time() - (cleanup_hours * 3600)
    
    for directory in [TTS_AUDIO_DIR, VOICEMAIL_DIR]:
        if not directory.exists():
            continue
            
        for file_path in directory.glob("*"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    print(f"🗑️ [Cleanup] Removed old file: {file_path.name}")
            except Exception as e:
                print(f"⚠️ [Cleanup] Failed to remove {file_path.name}: {e}")
"""

# === OPTION 3: Size-Based Cleanup ===

# Add this function for storage management:
"""
async def cleanup_by_size():
    '''Keep only the most recent files within size limit'''
    max_size_mb = int(os.getenv("MAX_STORAGE_MB", "500"))  # Default 500MB
    max_size_bytes = max_size_mb * 1024 * 1024
    
    for directory in [TTS_AUDIO_DIR, VOICEMAIL_DIR]:
        if not directory.exists():
            continue
            
        # Get all files sorted by modification time (newest first)
        files = sorted(directory.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        total_size = 0
        for file_path in files:
            file_size = file_path.stat().st_size
            total_size += file_size
            
            if total_size > max_size_bytes:
                try:
                    file_path.unlink()
                    print(f"🗑️ [Size Cleanup] Removed: {file_path.name} ({file_size} bytes)")
                except Exception as e:
                    print(f"⚠️ [Size Cleanup] Failed to remove {file_path.name}: {e}")
"""

# === ENVIRONMENT VARIABLES FOR CLEANUP CONFIGURATION ===

print("""
Add these to your .env file to enable cleanup:

# === File Cleanup Configuration ===
AUTO_CLEANUP_FILES=false          # true = immediate cleanup after upload
CLEANUP_AFTER_HOURS=24            # Hours to keep files (for delayed cleanup)
MAX_STORAGE_MB=500                # Maximum storage for audio files
ENABLE_SCHEDULED_CLEANUP=true     # Enable periodic cleanup task

# === Cleanup Strategy Options ===
# IMMEDIATE: Files deleted right after successful Drive upload
# DELAYED: Files kept for X hours then deleted
# SIZE_BASED: Keep newest files up to storage limit
# NONE: Keep all files (current behavior)
CLEANUP_STRATEGY=DELAYED
""")

print("""
=== PROS & CONS OF AUTO-CLEANUP ===

✅ PROS:
• Saves local storage space
• Prevents disk full issues
• Automatic maintenance
• Configurable retention policies

❌ CONS:
• No local backup if Drive fails
• Cannot re-serve files from local storage
• TTS files need re-generation if requested again
• Harder debugging without local files

=== RECOMMENDATIONS ===

🎯 For Production: Enable DELAYED cleanup (24-48 hours)
   - Keeps files temporarily for immediate serving
   - Automatic cleanup prevents storage issues
   
🔧 For Development: Disable cleanup
   - Keep files for debugging
   - Manual cleanup when needed

💾 For Limited Storage: Enable SIZE_BASED cleanup
   - Always keeps newest files
   - Automatic old file removal
""")

if __name__ == "__main__":
    print("This script shows cleanup options. Choose based on your needs!")