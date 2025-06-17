import requests
import pathlib
import time
import os
from typing import Optional, Union, Tuple
from utils.paths import TTS_AUDIO_DIR
from utils.validators import sanitize_user_id, sanitize_filename, create_safe_path
from utils.rate_limiter import rate_limit, RateLimiter
from utils.logging import log_tts_async

# -------------------------------------------------------------------
#  Tiny helper that wraps NYCU's Taigi-TTS back-end in one call.
#
#  Requirements:  pip install requests
# -------------------------------------------------------------------

_GENDER_MAP = {"female": "女聲", "male": "男聲"}
_ACCENT_MAP = {
    "strong": "強勢腔（高雄腔）",
    "second": "次強勢腔（台北腔）",
}

# Rate limiter for Taigi service
taigi_limiter = RateLimiter(max_requests=30, window_seconds=60)  # 30 requests per minute

def taigi_tts(
    *,
    mandarin: Optional[str] = None,
    tlpa: Optional[str] = None,
    base: str = "http://tts001.iptcloud.net:8804",
    gender: str = "female",            # "female" or "male"
    accent: str = "strong",            # "strong" (Kaohsiung) or "second" (Taipei)
    outfile: Optional[Union[str, pathlib.Path]] = None,
) -> bytes:
    """
    Return Taiwanese speech as WAV bytes (and optionally save to disk).

    Parameters
    ----------
    mandarin : str
        Mandarin text to convert → TLPA → WAV.  Ignored if `tlpa` is supplied.
    tlpa : str
        TLPA string (numeric-tone romanisation).  If given, we skip conversion.
    base : str
        Origin that hosts the API endpoints.
    gender : {"female", "male"}
    accent : {"strong", "second"}
    outfile : path-like or str, optional
        If provided, the WAV is written there and the same bytes are returned.

    Returns
    -------
    bytes
        Raw WAV data.
    """
    if not (mandarin or tlpa):
        raise ValueError("Provide either mandarin= or tlpa=")

    base = base.rstrip("/")
    end_cn2tlpa  = "/html_taigi_zh_tw_py"
    end_tlpa2wav = "/synthesize_TLPA"

    # 1️⃣ Mandarin → TLPA (unless user supplied TLPA directly)
    if tlpa is None:
        r = requests.get(f"{base}{end_cn2tlpa}",
                         params={"text0": mandarin}, timeout=60)
        r.raise_for_status()
        tlpa = r.text.strip()
        if not tlpa:
            raise RuntimeError("Server returned empty TLPA string")

    # 2️⃣ TLPA → WAV
    params = {
        "text1": tlpa,
        "gender": _GENDER_MAP[gender],
        "accent": _ACCENT_MAP[accent],
    }
    r = requests.get(f"{base}{end_tlpa2wav}", params=params, timeout=120)
    r.raise_for_status()
    wav = r.content

    if outfile:
        path = pathlib.Path(outfile).expanduser().resolve()
        path.write_bytes(wav)

    return wav


@rate_limit(taigi_limiter, key_func=lambda text: "global")
def translate_to_taigi(text: str) -> str:
    """
    Translate Chinese text to Taiwanese (TLPA romanization).
    This is used as an intermediate step for translation display.
    
    Args:
        text: Chinese text to translate
        
    Returns:
        TLPA romanization of the Taiwanese translation
    """
    try:
        base = "http://tts001.iptcloud.net:8804"
        end_cn2tlpa = "/html_taigi_zh_tw_py"
        
        r = requests.get(
            f"{base}{end_cn2tlpa}",
            params={"text0": text},
            timeout=60
        )
        r.raise_for_status()
        
        tlpa = r.text.strip()
        if not tlpa:
            raise RuntimeError("Server returned empty TLPA string")
            
        return tlpa
        
    except Exception as e:
        print(f"[TAIGI] Translation error: {e}")
        return "⚠️ 台語翻譯服務暫時無法使用，請稍後再試。"

@rate_limit(taigi_limiter, key_func=lambda text, user_id: user_id)
def synthesize_taigi(text: str, user_id: str) -> Tuple[str, int]:
    """
    Synthesize Taiwanese speech from Chinese text.
    Returns (audio_url, duration_ms) similar to TTS service.
    
    Args:
        text: Chinese text to synthesize
        user_id: User ID for file naming
        
    Returns:
        Tuple of (audio_url, duration_ms)
    """
    try:
        # Sanitize inputs
        user_id = sanitize_user_id(user_id)
        
        # First get TLPA
        tlpa = translate_to_taigi(text)
        if tlpa.startswith("⚠️"):
            raise ValueError(tlpa)
        
        # Generate filename
        ts = time.strftime("%Y%m%d_%H%M%S")
        fn = f"{user_id}_taigi_{ts}.wav"
        safe_fn = sanitize_filename(fn)
        
        # Create path
        TTS_AUDIO_DIR.mkdir(exist_ok=True)
        path = create_safe_path(str(TTS_AUDIO_DIR), safe_fn)
        
        # Generate audio
        wav_bytes = taigi_tts(
            tlpa=tlpa,
            gender="female",
            accent="strong",
            outfile=str(path)
        )
        
        # Calculate duration (assume 16kHz for rough estimate)
        # WAV header is typically 44 bytes
        audio_data_size = len(wav_bytes) - 44
        # 16-bit audio = 2 bytes per sample
        duration_ms = int((audio_data_size / 2 / 16000) * 1000)
        
        # Build URL
        base_url = os.getenv("BASE_URL", "")
        if base_url and "YOUR_DOMAIN" not in base_url:
            url = f"{base_url}/static/{safe_fn}"
        else:
            url = f"/static/{safe_fn}"
        
        # Log to database (async)
        log_tts_async(user_id, text, str(path), url)
        
        return url, duration_ms
        
    except Exception as e:
        print(f"[TAIGI] TTS error: {e}")
        raise ValueError(f"台語語音合成失敗：{str(e)}")

# For testing:
if __name__ == "__main__":
    # Test translation
    tlpa = translate_to_taigi("今天天氣很好")
    print(f"TLPA: {tlpa}")
    
    # Test TTS
    wav_bytes = taigi_tts(
        mandarin="今天天氣很好",
        gender="female",
        accent="strong",
        outfile="test_taigi.wav"
    )
    print(f"Generated {len(wav_bytes)} bytes")