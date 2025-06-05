from __future__ import annotations
import os, time, wave
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── internal helper ───────────────────────────────────────────────
def _wave_file(path, pcm, *, ch=1, rate=24_000, sampwidth=2):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# ── public API ────────────────────────────────────────────────────
def synthesize(text: str, user_id: str, voice_name: str = "Kore") -> tuple[str, int]:
    """
    Returns  (absolute_url , duration_ms)
    The file is saved under  /tts_audio.
    """
    ts   = time.strftime("%Y%m%d_%H%M%S")
    fn   = f"{user_id}_{ts}.wav"
    path = os.path.join("tts_audio", fn)

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
    pcm = resp.candidates[0].content.parts[0].inline_data.data
    _wave_file(path, pcm)

    # duration = samples / (rate*channels) * 1000
    dur_ms = int(len(pcm) / (24_000 * 2) * 1000)
    base   = os.getenv("BASE_URL", "https://YOUR_DOMAIN")
    url    = f"{base}/static/{fn}"
    return url, dur_ms
