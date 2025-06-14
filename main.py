from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from pathlib import Path
from routes.webhook import webhook_router
from handlers.session_manager import get_user_session, cleanup_expired_sessions
from handlers.logic_handler import handle_user_message
from utils.paths import TTS_AUDIO_DIR
import asyncio
from contextlib import asynccontextmanager

# BUG FIX: Background task for session cleanup
# Previously: Sessions never expired, causing memory leaks
async def periodic_session_cleanup():
    """Run session cleanup every hour"""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            cleanup_expired_sessions()  # This is not async
        except Exception as e:
            print(f"Error during session cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(periodic_session_cleanup())
    yield
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

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

# ── local dev ----------------------------------------------------------test#
if __name__ == "__main__":
    import uvicorn, os
    port = int(os.getenv("PORT", 10001))   # default 10001
    uvicorn.run("main:app", host="0.0.0.0", port=port)

