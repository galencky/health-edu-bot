"""
Mededbot Main Application - FastAPI LINE Bot with Gemini AI
Handles webhook endpoints, health checks, and background tasks
"""
import os
import sys
import io
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routes.webhook import webhook_router
from handlers.session_manager import get_user_session, cleanup_expired_sessions
from handlers.logic_handler import handle_user_message
from utils.paths import TTS_AUDIO_DIR
from utils.validators import sanitize_filename
from utils.storage_config import TTS_USE_MEMORY
from utils.memory_storage import memory_storage

# ============================================================
# INITIALIZATION
# ============================================================

load_dotenv()

# Force unbuffered output for Docker logs
sys.stdout.flush()
sys.stderr.flush()

# ============================================================
# BACKGROUND TASKS
# ============================================================

async def periodic_session_cleanup():
    """
    Clean up expired user sessions every hour
    Prevents memory leaks from abandoned sessions
    """
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            removed_count = cleanup_expired_sessions()
            if removed_count > 0:
                print(f"🧹 Session cleanup: removed {removed_count} expired sessions", flush=True)
                
        except asyncio.CancelledError:
            print("🛑 Session cleanup task cancelled", flush=True)
            break
        except Exception as e:
            print(f"❌ Session cleanup error: {e}", flush=True)
            continue

async def periodic_tts_cleanup():
    """
    Clean up old TTS audio files from disk storage
    - Removes files older than 24 hours
    - Enforces 500MB directory size limit
    """
    if TTS_USE_MEMORY:
        return  # Skip if using memory storage
    
    from utils.cleanup import cleanup_tts_directory_by_size, cleanup_old_tts_files
    
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            # Remove old files first
            old_count = cleanup_old_tts_files(TTS_AUDIO_DIR, max_age_hours=24)
            
            # Then enforce size limit
            size_count = cleanup_tts_directory_by_size(TTS_AUDIO_DIR, max_size_mb=500)
            
            if old_count > 0 or size_count > 0:
                print(f"🧹 TTS cleanup: {old_count} old files, {size_count} for size", flush=True)
                
        except asyncio.CancelledError:
            print("🛑 TTS cleanup task cancelled", flush=True)
            break
        except Exception as e:
            print(f"❌ TTS cleanup error: {e}", flush=True)
            continue

async def periodic_memory_cleanup():
    """
    Clean up old files from in-memory storage
    Prevents out-of-memory errors in ephemeral deployments
    """
    if not TTS_USE_MEMORY:
        return  # Skip if using disk storage
    
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            # Remove files older than 24 hours
            removed = memory_storage.cleanup_old_files(max_age_seconds=86400)
            if removed > 0:
                print(f"🧹 Memory cleanup: removed {removed} old files", flush=True)
                
        except asyncio.CancelledError:
            print("🛑 Memory cleanup task cancelled", flush=True)
            break
        except Exception as e:
            print(f"❌ Memory cleanup error: {e}", flush=True)
            continue

# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    - Startup: Initialize background tasks and test connections
    - Shutdown: Clean up resources gracefully
    """
    # ========== STARTUP ==========
    
    # Start session cleanup task
    session_task = asyncio.create_task(periodic_session_cleanup())
    
    # Start storage-specific cleanup task
    storage_task = None
    if TTS_USE_MEMORY:
        print("🧠 Using in-memory storage for TTS files", flush=True)
        storage_task = asyncio.create_task(periodic_memory_cleanup())
    else:
        print("💾 Using local disk storage for TTS files", flush=True)
        storage_task = asyncio.create_task(periodic_tts_cleanup())
    
    # Test database connection
    await _test_database_connection()
    
    yield
    
    # ========== SHUTDOWN ==========
    
    print("🛑 Starting graceful shutdown...", flush=True)
    
    # Cancel background tasks
    session_task.cancel()
    if storage_task:
        storage_task.cancel()
    
    # Wait for task cancellation
    await _wait_for_task(session_task, "session cleanup")
    if storage_task:
        await _wait_for_task(storage_task, "storage cleanup")
    
    # Clean up resources
    await _cleanup_resources()
    
    print("✅ Graceful shutdown completed", flush=True)


async def _test_database_connection():
    """Test database connectivity on startup"""
    try:
        from utils.database import get_async_db_engine
        from sqlalchemy import text
        
        engine = get_async_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ [DB] Connected to Neon database", flush=True)
        
    except Exception as e:
        print(f"⚠️  [DB] Database connection failed: {e}", flush=True)


async def _wait_for_task(task: asyncio.Task, name: str):
    """Wait for a task to cancel gracefully"""
    try:
        await task
    except asyncio.CancelledError:
        print(f"✅ {name} task cancelled", flush=True)


async def _cleanup_resources():
    """Clean up resources during shutdown"""
    # Shutdown logging executor
    try:
        from utils.logging import _logging_executor
        _logging_executor.shutdown(wait=True)
        print("📝 Logging executor shutdown", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to shutdown logging: {e}", flush=True)
    
    # Final session cleanup
    try:
        removed = cleanup_expired_sessions()
        if removed > 0:
            print(f"🗑️ Final cleanup: {removed} sessions", flush=True)
    except Exception as e:
        print(f"⚠️ Final session cleanup failed: {e}", flush=True)
    
    # Clear memory storage
    if TTS_USE_MEMORY:
        try:
            memory_storage.clear_all()
            print("🧠 Memory storage cleared", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to clear memory: {e}", flush=True)

# ============================================================
# APPLICATION SETUP
# ============================================================

app = FastAPI(
    title="Mededbot",
    description="LINE Bot with Gemini AI for health education",
    version="2.0",
    lifespan=lifespan
)

# Mount static files directory (with path traversal protection)
app.mount("/static", StaticFiles(directory=str(TTS_AUDIO_DIR)), name="static")

# Include webhook router
app.include_router(webhook_router, prefix="/webhook")

# ============================================================
# API ENDPOINTS
# ============================================================

class UserInput(BaseModel):
    """Chat endpoint input model"""
    message: str


class ChatResponse(BaseModel):
    """Chat endpoint response model"""
    reply: str
    quick_reply: Optional[Dict] = None


@app.post("/chat", response_model=ChatResponse)
def chat(input: UserInput) -> ChatResponse:
    """
    Test endpoint for chat functionality
    
    Args:
        input: User message
        
    Returns:
        Bot reply with optional quick reply buttons
    """
    try:
        # Use test user ID for this endpoint
        user_id = "test-user"
        session = get_user_session(user_id)
        
        # Process message
        reply, _, quick_reply_data = handle_user_message(
            user_id, 
            input.message, 
            session
        )
        
        return ChatResponse(reply=reply, quick_reply=quick_reply_data)
        
    except Exception as e:
        print(f"[CHAT] Error: {e}")
        return ChatResponse(
            reply="⚠️ 系統異常，請稍後再試。",
            quick_reply=None
        )




@app.api_route("/", methods=["GET", "HEAD"])
def root():
    """
    Root endpoint - service information
    """
    return {
        "service": "Mededbot",
        "description": "LINE Bot with Gemini AI for health education",
        "status": "online",
        "endpoints": {
            "webhook": "/webhook",
            "chat": "/chat",
            "health": "/health",
            "ping": "/ping"
        }
    }


@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    """
    Simple ping endpoint for uptime monitoring
    """
    return Response(
        content='{"status": "ok", "timestamp": "' + datetime.now().isoformat() + '"}',
        media_type="application/json"
    )


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """
    Health check endpoint for container orchestration
    Returns lightweight status without heavy operations
    """
    response = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Add optional metrics if available
        if TTS_USE_MEMORY:
            memory_info = memory_storage.get_info()
            response["memory_files"] = memory_info["files"]
        
        from handlers.session_manager import get_session_count
        response["active_sessions"] = get_session_count()
        
    except Exception:
        pass  # Don't fail health check on metrics error
    
    return response


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """
    Serve TTS audio files from memory storage
    Only available in ephemeral deployments (TTS_USE_MEMORY=true)
    
    Args:
        filename: Audio filename to retrieve
        
    Returns:
        Audio file stream
    """
    if not TTS_USE_MEMORY:
        raise HTTPException(
            status_code=404,
            detail="Audio endpoint not available in disk storage mode"
        )
    
    try:
        # Validate and sanitize filename
        safe_filename = sanitize_filename(filename)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename format"
        )
    
    # Retrieve from memory storage
    result = memory_storage.get(safe_filename)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Audio file not found or expired"
        )
    
    data, content_type = result
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="{safe_filename}"'
        }
    )

# ============================================================
# DEVELOPMENT SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    from utils.uvicorn_logging import get_uvicorn_log_config
    
    # Server configuration
    port = int(os.getenv("PORT", 8080))
    log_config = get_uvicorn_log_config()
    
    print(f"🚀 Starting Mededbot on port {port}...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_config=log_config,
        timeout_keep_alive=75,  # Extended for NAS deployment
        access_log=False       # Reduce I/O for better performance
    )

