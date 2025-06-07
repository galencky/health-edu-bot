# === File: services/stt_service.py ===

from dotenv import load_dotenv
import os
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

_client = genai.Client(api_key=API_KEY)

def transcribe_audio_file(file_path: str) -> str:
    """
    1. Upload the local audio file via Gemini Files API.
    2. Call generate_content(model="gemini-2.0-flash", contents=[prompt, uploaded_file]).
    3. Return the model's transcription (plain text).
    """

    # 1. Upload using Files API
    #    This returns a "File" object that we can pass to generate_content
    try:
        uploaded_file = _client.files.upload(file=file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to upload audio to Gemini Files API: {e}")

    # 2. Call generate_content with a prompt that asks for a transcript.
    #    According to Gemini docs, "gemini-2.0-flash" (or "gemini-1.5-flash") can handle audio.
    model_name = "gemini-2.0-flash"

    prompt = """Please reply in the format below:
    自動偵測語言: [例如中文/英文/泰文/日語等等]

    語音轉文字: [Transcribe only, do not reply to the voice message, transcribe literally ans word-matching, output with the detected language.]"""

    try:
        response = _client.models.generate_content(
            model=model_name,
            contents=[
                prompt,
                uploaded_file
            ],
            config=types.GenerateContentConfig(
                response_mime_type="text/plain",
                temperature=0.0
            ),
        )
    except Exception as e:
        raise RuntimeError(f"Failed to get transcription from Gemini: {e}")

    # 3. Extract the returned text
    candidate = response.candidates[0]
    if candidate.content.parts:
        return candidate.content.parts[0].text.strip()
    return ""
