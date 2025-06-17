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
    """Run session cleanup every hour - simple and stable like old version"""
    while True:
        await asyncio.sleep(3600)  # 1 hour - same as stable old version
        try:
            # Simple cleanup without thread pool complexity
            cleanup_expired_sessions()
            print(f"🧹 Session cleanup completed", flush=True)
        except Exception as e:
            print(f"Error during session cleanup: {e}", flush=True)

# Background task for TTS file cleanup
async def periodic_tts_cleanup():
    """Clean up old TTS files every hour to prevent disk space issues"""
    from utils.cleanup import cleanup_tts_directory_by_size, cleanup_old_tts_files
    from utils.storage_config import TTS_USE_MEMORY
    
    # Only run if using disk storage
    if TTS_USE_MEMORY:
        return
    
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            # First remove old files (>24 hours)
            old_count = cleanup_old_tts_files(TTS_AUDIO_DIR, max_age_hours=24)
            
            # Then check size limit (500MB)
            size_count = cleanup_tts_directory_by_size(TTS_AUDIO_DIR, max_size_mb=500)
            
            if old_count > 0 or size_count > 0:
                print(f"🧹 TTS cleanup completed: {old_count} old files, {size_count} for size limit", flush=True)
        except Exception as e:
            print(f"Error during TTS cleanup: {e}", flush=True)

# Removed complex rate limiter cleanup - not needed in stable old version

# Removed complex memory and disk cleanup tasks - not needed in stable old version
# The old version just relied on simple periodic cleanup which works fine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Keep it simple like the old stable version
    cleanup_task = asyncio.create_task(periodic_session_cleanup())
    
    # Add TTS cleanup task if using disk storage
    tts_cleanup_task = None
    if TTS_USE_MEMORY:
        print("🧠 Using in-memory storage for TTS files", flush=True)
    else:
        print("💾 Using local disk storage for TTS files", flush=True)
        tts_cleanup_task = asyncio.create_task(periodic_tts_cleanup())
    
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
    
    # Graceful shutdown - simple like old version
    print("🛑 Starting graceful shutdown...", flush=True)
    
    # Cancel cleanup tasks
    cleanup_task.cancel()
    if tts_cleanup_task:
        tts_cleanup_task.cancel()
    
    # Wait for tasks to complete
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    if tts_cleanup_task:
        try:
            await tts_cleanup_task
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
    """Synchronous endpoint to avoid thread hop overhead"""
    try:
        user_id = "test-user"                     # stub ID for this endpoint
        session = get_user_session(user_id)
        
        # Direct sync call - no thread pool needed
        reply, _, quick_reply_data = handle_user_message(
            user_id, 
            input.message, 
            session
        )
        return {"reply": reply, "quick_reply": quick_reply_data}
    except Exception as e:
        print(f"[CHAT] Error: {e}")
        return {"reply": "⚠️ 系統異常，請稍後再試。", "quick_reply": None}




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
    
    port = int(os.getenv("PORT", 8080))   # default 8080
    log_config = get_uvicorn_log_config()
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port,
        log_config=log_config,
        # Keepalive settings for long-running NAS deployment
        timeout_keep_alive=75,  # Keep connections alive longer
        access_log=False  # Reduce I/O on NAS
    )

