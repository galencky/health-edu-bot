# === File: services/tts_service.py ===
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from utils.paths import TTS_AUDIO_DIR

import os, time, wave
from google import genai
from google.genai import types

from utils.logging import log_tts_async

# Load environment
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# BUG FIX: Function to list available models for debugging
def list_available_models():
    """List available Gemini models for debugging TTS issues"""
    try:
        models = client.models.list()
        audio_models = []
        for model in models:
            # Look for models that support audio generation
            if hasattr(model, 'supported_generation_methods'):
                if 'generateContent' in model.supported_generation_methods:
                    audio_models.append(model.name)
        print(f"[TTS DEBUG] Available models: {audio_models[:5]}...")  # Show first 5
        return audio_models
    except Exception as e:
        print(f"[TTS DEBUG] Could not list models: {e}")
        return []

# Internal helper: Save raw PCM as WAV
def _wave_file(path, pcm, *, ch=1, rate=24_000, sampwidth=2):
    """
    Save PCM bytes as a .wav file at the given path.
    Ensures path is a string before passing to wave.open.
    """
    with wave.open(str(path), "wb") as wf:  # 🔧 Convert Path to str
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
    
    BUG FIX: Added comprehensive error handling for TTS failures
    """
    # BUG FIX: Validate input text
    # Previously: No validation could cause API failures
    if not text or not text.strip():
        raise ValueError("Cannot synthesize empty text")
    
    # Limit text length to prevent API errors (5000 chars is a safe limit)
    MAX_TTS_LENGTH = 5000
    if len(text) > MAX_TTS_LENGTH:
        print(f"[TTS WARNING] Text too long ({len(text)} chars), truncating to {MAX_TTS_LENGTH}")
        text = text[:MAX_TTS_LENGTH] + "..."
    
    ts   = time.strftime("%Y%m%d_%H%M%S")
    fn   = f"{user_id}_{ts}.wav"
    path = TTS_AUDIO_DIR / fn

    try:
        # Generate audio using Gemini
        # BUG FIX: Use the correct Gemini 2.5 Flash Preview TTS model name from documentation
        tts_model = "gemini-2.5-flash-preview-tts"  # Dedicated TTS model
        #print(f"[TTS DEBUG] Using model: {tts_model}, Voice: {voice_name}")
        
        resp = client.models.generate_content(
            model=tts_model,
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
            
    except Exception as e:
        # BUG FIX: Catch other API errors
        raise ValueError(f"TTS API call failed: {str(e)}")

    # BUG FIX: Add proper error handling for TTS response
    # Previously: AttributeError when response has no candidates or parts
    if not resp or not resp.candidates:
        print(f"[TTS DEBUG] Empty response. Text length: {len(text)}, Text preview: {text[:100]}...")
        raise ValueError("TTS service returned empty response")
    
    if not resp.candidates[0].content or not resp.candidates[0].content.parts:
        print(f"[TTS DEBUG] No content/parts. Candidate: {resp.candidates[0]}")
        raise ValueError("TTS response has no audio content")
    
    if not resp.candidates[0].content.parts[0].inline_data:
        print(f"[TTS DEBUG] No inline data. Parts: {resp.candidates[0].content.parts}")
        raise ValueError("TTS response has no inline audio data")
    
    # Extract audio and save as .wav
    pcm = resp.candidates[0].content.parts[0].inline_data.data
    if not pcm:
        raise ValueError("TTS response contains empty audio data")
    
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
    log_tts_async(user_id, text, path, url)

    return url, dur_ms
