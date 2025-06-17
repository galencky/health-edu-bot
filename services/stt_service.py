# === File: services/stt_service.py ===

from dotenv import load_dotenv
load_dotenv()

import os
import mimetypes
from google import genai
from google.genai import types


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
        # Try file upload first (simpler approach)
        try:
            uploaded_file = _client.files.upload(file=file_path)
        except Exception as first_error:
            # If file upload fails (likely Docker MIME detection issue), 
            # use inline audio data approach with explicit MIME type
            if "mime type" in str(first_error).lower():
                # Read audio file as bytes for inline approach
                with open(file_path, 'rb') as f:
                    audio_bytes = f.read()
                
                # Detect MIME type for inline data
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    ext = file_path.lower().split('.')[-1]
                    mime_map = {
                        'm4a': 'audio/mp4',
                        'aac': 'audio/aac', 
                        'mp3': 'audio/mp3',  # Use audio/mp3 as per docs
                        'wav': 'audio/wav',
                        'ogg': 'audio/ogg',
                        'flac': 'audio/flac',
                        'aiff': 'audio/aiff'
                    }
                    mime_type = mime_map.get(ext, 'audio/mp3')
                
                # Create inline audio part
                uploaded_file = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            else:
                raise first_error
    except Exception as e:
        raise RuntimeError(f"Failed to upload audio to Gemini Files API: {e}")

    # 2. Call generate_content with a prompt that asks for a transcript.
    #    According to Gemini docs, "gemini-2.0-flash" (or "gemini-1.5-flash") can handle audio.
    model_name = "gemini-2.0-flash"

    prompt = """
You are a transcription assistant.    
- Do NOT add any comments, replies, or explanations—output only the transcript.   
- Correct obvious speaking errors (e.g. mispronunciations) and remove filler words (“um”, “uh”, stutters) for fluent, readable text.   
- Preserve the speaker’s original meaning and phrasing as much as possible.
"""

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
