import requests
import pathlib
from typing import Optional, Union

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


# Example 1 – from Mandarin
wav_bytes = taigi_tts(
    mandarin="今天天氣很好，我們一起出去玩。",
    gender="female",
    accent="strong",
    outfile="speech.wav"      # omit if you only need the bytes
)
print("Saved  speech.wav  ({} bytes)".format(len(wav_bytes)))