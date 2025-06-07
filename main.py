from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from routes.webhook import webhook_router
from handlers.session_manager import get_user_session
from handlers.logic_handler import handle_user_message
from utils.paths import TTS_AUDIO_DIR



app = FastAPI()

# Add BEFORE app.include_router(...)
app.mount("/static", StaticFiles(directory=str(TTS_AUDIO_DIR)), name="static")


app.include_router(webhook_router)

# ── simple test endpoint ----------------------------------------------
class UserInput(BaseModel):
    message: str

@app.post("/chat")
def chat(input: UserInput):
    user_id = "test-user"                     # stub ID for this endpoint
    session = get_user_session(user_id)
    reply, _ = handle_user_message(user_id, input.message, session)
    return {"reply": reply}

# ── misc endpoints -----------------------------------------------------
@app.get("/")
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

