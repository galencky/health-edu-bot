"""
Mededbot Main Application
"""
import os
import sys
import io
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

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

load_dotenv()

# Force unbuffered output
sys.stdout.flush()
sys.stderr.flush()

# Background tasks
async def periodic_cleanup():
    """Clean up expired sessions and old files every hour"""
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            
            # Clean sessions
            cleanup_expired_sessions()
            
            # Clean storage
            if TTS_USE_MEMORY:
                memory_storage.cleanup_old_files(max_age_seconds=86400)
            else:
                from utils.cleanup import cleanup_tts_directory_by_size, cleanup_old_tts_files
                cleanup_old_tts_files(TTS_AUDIO_DIR, max_age_hours=24)
                cleanup_tts_directory_by_size(TTS_AUDIO_DIR, max_size_mb=500)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[CLEANUP] Error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    # Test database
    try:
        from utils.database import get_async_db_engine
        from sqlalchemy import text
        engine = get_async_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connected")
    except Exception as e:
        print(f"⚠️ Database error: {e}")
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    # Final cleanup
    cleanup_expired_sessions()
    if TTS_USE_MEMORY:
        memory_storage.clear_all()

# Create app
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(TTS_AUDIO_DIR)), name="static")
app.include_router(webhook_router)

# Endpoints
class UserInput(BaseModel):
    message: str

@app.post("/chat")
def chat(input: UserInput):
    """Test endpoint for chat functionality"""
    try:
        user_id = "test-user"
        session = get_user_session(user_id)
        reply, _, quick_reply = handle_user_message(user_id, input.message, session)
        return {"reply": reply, "quick_reply": quick_reply}
    except Exception as e:
        return {"reply": "⚠️ 系統異常，請稍後再試。", "quick_reply": None}

@app.get("/")
def root():
    """Service information"""
    return {
        "service": "Mededbot",
        "status": "online",
        "endpoints": ["/", "/chat", "/health", "/ping", "/webhook"]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    """Simple ping endpoint for monitoring"""
    return {"status": "ok"}

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve audio files from memory storage"""
    if not TTS_USE_MEMORY:
        raise HTTPException(404, "Not available in disk mode")
    
    try:
        safe_filename = sanitize_filename(filename)
        result = memory_storage.get(safe_filename)
        if not result:
            raise HTTPException(404, "File not found")
        
        data, content_type = result
        return StreamingResponse(io.BytesIO(data), media_type=content_type)
    except ValueError:
        raise HTTPException(400, "Invalid filename")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, access_log=False)