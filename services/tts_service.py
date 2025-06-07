# === File: services/tts_service.py ===

from __future__ import annotations
import os, time, wave
from dotenv import load_dotenv
from google import genai
from google.genai import types
from utils.tts_log import log_tts_to_drive_and_sheet

# Load environment
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Internal helper: Save raw PCM as WAV
def _wave_file(path, pcm, *, ch=1, rate=24_000, sampwidth=2):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# Public TTS function
def synthesize(text: str, user_id: str, voice_name: str = "Kore") -> tuple[str, int]:
    """
    Synthesizes speech using Gemini API.
    
    Returns:
        (audio_url, duration_ms) tuple
    Saves WAV to ./tts_audio and uploads to Google Drive in background.
    """
    ts   = time.strftime("%Y%m%d_%H%M%S")
    fn   = f"{user_id}_{ts}.wav"
    path = os.path.join("tts_audio", fn)

    # Generate audio using Gemini
    resp = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        ),
    )

    # Extract audio and save as .wav
    pcm = resp.candidates[0].content.parts[0].inline_data.data
    _wave_file(path, pcm)

    # Calculate duration (ms)
    dur_ms = int(len(pcm) / (24_000 * 2) * 1000)

    # Build public URL
    base = os.getenv("BASE_URL")
    if not base or "YOUR_DOMAIN" in base:
        raise RuntimeError(
            "BASE_URL environment variable is not set correctly. "
            "Cannot generate valid audio URL for LINE."
        )

    url = f"{base}/static/{fn}"

    # Log to Google Drive & Sheets (in background)
    log_tts_to_drive_and_sheet(user_id, text, path, url)

    return url, dur_ms
