from dotenv import load_dotenv
load_dotenv()

import sys

# Force unbuffered output for Docker logs
sys.stdout.flush()
sys.stderr.flush()

from fastapi import FastAPI, Response, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
from pathlib import Path
from routes.webhook import webhook_router
from handlers.session_manager import get_user_session, cleanup_expired_sessions
from handlers.logic_handler import handle_user_message
from utils.paths import TTS_AUDIO_DIR
from utils.validators import sanitize_text, sanitize_filename
from utils.storage_config import TTS_USE_MEMORY
from utils.memory_storage import memory_storage
import asyncio
from contextlib import asynccontextmanager
import io
from datetime import datetime

# BUG FIX: Background task for session cleanup with rate limiter cleanup
# Previously: Sessions never expired, causing memory leaks
async def periodic_session_cleanup():
    """Run session cleanup every hour"""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            # Run session cleanup in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, cleanup_expired_sessions)
            
            # Cleanup rate limiter memory to prevent memory leaks
            await cleanup_rate_limiter_memory()
            
            print(f"🧹 Session and rate limiter cleanup completed", flush=True)
        except Exception as e:
            print(f"❌ Error during cleanup: {e}", flush=True)

async def cleanup_rate_limiter_memory():
    """Clean up old rate limiter entries to prevent memory leaks"""
    try:
        from utils.rate_limiter import (
            gemini_limiter, tts_limiter, email_limiter, webhook_limiter
        )
        
        # Clean up all global rate limiters
        total_removed = 0
        limiters = [
            ("Gemini", gemini_limiter),
            ("TTS", tts_limiter), 
            ("Email", email_limiter),
            ("Webhook", webhook_limiter)
        ]
        
        for name, limiter in limiters:
            removed = limiter.cleanup_old_entries(max_age_seconds=7200)  # 2 hours
            total_removed += removed
            if removed > 0:
                print(f"🧹 {name} rate limiter: removed {removed} old entries", flush=True)
        
        if total_removed > 0:
            print(f"🧹 Rate limiter cleanup: {total_removed} total entries removed", flush=True)
        
    except Exception as e:
        print(f"⚠️ Rate limiter cleanup error: {e}", flush=True)

# Background task for memory storage cleanup (if using memory backend)
async def periodic_memory_cleanup():
    """Run memory storage cleanup every 30 minutes"""
    if not TTS_USE_MEMORY:
        return
    
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            memory_storage.cleanup_old_files(max_age_seconds=3600)  # Remove files older than 1 hour
            info = memory_storage.get_info()
            print(f"📊 Memory storage: {info['files']} files, {info['total_size_mb']:.1f} MB", flush=True)
        except Exception as e:
            print(f"Error during memory cleanup: {e}", flush=True)

# Background task for disk cleanup (if using local storage)
async def periodic_disk_cleanup():
    """Run disk cleanup every hour for local storage"""
    if TTS_USE_MEMORY:
        return  # Only run for local storage
    
    from utils.cleanup import cleanup_old_tts_files, get_directory_size
    
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            # Remove files older than 24 hours
            deleted = cleanup_old_tts_files(TTS_AUDIO_DIR, max_age_hours=24)
            
            # Check directory size
            size_bytes, file_count = get_directory_size(TTS_AUDIO_DIR)
            size_mb = size_bytes / 1024 / 1024
            print(f"📊 TTS directory: {file_count} files, {size_mb:.1f} MB", flush=True)
        except Exception as e:
            print(f"Error during disk cleanup: {e}", flush=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(periodic_session_cleanup())
    
    # Start memory cleanup if using memory backend
    memory_cleanup_task = None
    if TTS_USE_MEMORY:
        memory_cleanup_task = asyncio.create_task(periodic_memory_cleanup())
        print("🧠 Using in-memory storage for TTS files", flush=True)
    
    # Start disk cleanup if using local storage
    disk_cleanup_task = None
    if not TTS_USE_MEMORY:
        disk_cleanup_task = asyncio.create_task(periodic_disk_cleanup())
        print("💾 Using local disk storage for TTS files", flush=True)
    
    # Test database connection
    try:
        from utils.database import get_async_db_engine
        from sqlalchemy import text
        engine = get_async_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ [DB] Successfully connected to Neon database", flush=True)
    except Exception as e:
        print(f"⚠️  [DB] Database connection failed: {e}", flush=True)
    
    yield
    
    # Graceful shutdown with comprehensive resource cleanup
    print("🛑 Starting graceful shutdown...", flush=True)
    
    # Cancel background tasks
    cleanup_task.cancel()
    if memory_cleanup_task:
        memory_cleanup_task.cancel()
    if disk_cleanup_task:
        disk_cleanup_task.cancel()
    
    # Wait for tasks to complete
    try:
        await cleanup_task
        if memory_cleanup_task:
            await memory_cleanup_task
        if disk_cleanup_task:
            await disk_cleanup_task
    except asyncio.CancelledError:
        pass
    
    # Shutdown thread pool executors to prevent resource leaks
    try:
        from utils.logging import _logging_executor
        print("📝 Shutting down logging executor...", flush=True)
        _logging_executor.shutdown(wait=True)
    except Exception as e:
        print(f"⚠️ Failed to shutdown logging executor: {e}", flush=True)
    
    # Final session cleanup to free memory
    try:
        final_removed = cleanup_expired_sessions()
        print(f"🗑️ Final cleanup: removed {final_removed} sessions", flush=True)
    except Exception as e:
        print(f"⚠️ Final session cleanup failed: {e}", flush=True)
    
    # Clear memory storage
    if TTS_USE_MEMORY:
        try:
            memory_storage.clear_all()
            print("🧠 Cleared all memory storage", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to clear memory storage: {e}", flush=True)
    
    print("✅ Graceful shutdown completed", flush=True)

app = FastAPI(lifespan=lifespan)

# BUG FIX: Path traversal protection for static files
# Previously: No validation allowed access to files outside TTS_AUDIO_DIR
# Now: Using StaticFiles with proper directory restriction
app.mount("/static", StaticFiles(directory=str(TTS_AUDIO_DIR)), name="static")


app.include_router(webhook_router)

# ── simple test endpoint ----------------------------------------------
class UserInput(BaseModel):
    message: str

@app.post("/chat")
def chat(input: UserInput):
    user_id = "test-user"                     # stub ID for this endpoint
    session = get_user_session(user_id)
    reply, _, quick_reply_data = handle_user_message(user_id, input.message, session)
    return {"reply": reply, "quick_reply": quick_reply_data}




# ── misc endpoints -----------------------------------------------------
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {
        "message": "✅ FastAPI LINE + Gemini bot is running.",
        "status": "Online",
        "endpoints": ["/", "/chat", "/ping", "/webhook"],
    }

@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    return Response(content='{"status": "ok"}', media_type="application/json")

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Lightweight health check endpoint optimized for container health checks"""
    try:
        # Quick memory check
        from utils.memory_storage import memory_storage
        memory_info = memory_storage.get_info()
        
        # Quick session count check
        from handlers.session_manager import get_session_count
        session_count = get_session_count()
        
        # Basic response - don't do heavy operations in health check
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory_files": memory_info["files"],
            "active_sessions": session_count
        }
    except Exception:
        # Don't expose internal errors in health check
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ── audio endpoint for memory storage ---------------------------------
@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve audio files from memory storage (for ephemeral deployments)"""
    if not TTS_USE_MEMORY:
        raise HTTPException(404, "Audio endpoint not available in this deployment")
    
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
    except ValueError:
        raise HTTPException(400, "Invalid filename")
    
    # Get from memory
    result = memory_storage.get(safe_filename)
    if not result:
        raise HTTPException(404, "Audio file not found")
    
    data, content_type = result
    return StreamingResponse(io.BytesIO(data), media_type=content_type)

# ── local dev ----------------------------------------------------------test#
if __name__ == "__main__":
    import uvicorn, os
    from utils.uvicorn_logging import get_uvicorn_log_config
    
    port = int(os.getenv("PORT", 10001))   # default 10001
    log_config = get_uvicorn_log_config()
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port,
        log_config=log_config
    )

