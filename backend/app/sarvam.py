"""Sarvam AI : synthese vocale (TTS) et transcription (STT)."""
from __future__ import annotations

import httpx

from .config import settings

TTS_URL = "https://api.sarvam.ai/text-to-speech"
STT_URL = "https://api.sarvam.ai/speech-to-text"

# langue de l'app -> code Sarvam (langues indiennes + anglais indien)
LANG_CODE = {"hi": "hi-IN", "en": "en-IN", "ta": "ta-IN", "bn": "bn-IN", "te": "te-IN"}


async def text_to_speech(text: str, lang: str = "hi", speaker: str = "anushka") -> str | None:
    """Retourne l'audio (base64 WAV) ou None si non supporte / erreur."""
    code = LANG_CODE.get(lang)
    if not code or not settings.sarvam_api_key or not text:
        return None
    try:
        async with httpx.AsyncClient(timeout=40) as cl:
            r = await cl.post(TTS_URL,
                headers={"api-subscription-key": settings.sarvam_api_key, "Content-Type": "application/json"},
                json={"text": text[:1500], "target_language_code": code, "speaker": speaker, "model": "bulbul:v2"})
            if r.status_code != 200:
                return None
            audios = r.json().get("audios") or []
            return audios[0] if audios else None
    except Exception:
        return None


async def speech_to_text(audio_bytes: bytes, lang: str = "hi",
                         filename: str = "audio.wav") -> str | None:
    """Transcrit un audio via Sarvam (saarika:v2.5) dans la langue d'origine."""
    if not settings.sarvam_api_key or not audio_bytes:
        return None
    code = LANG_CODE.get(lang, "hi-IN")
    ext = filename.rsplit(".", 1)[-1].lower()
    ct = {"webm": "audio/webm", "m4a": "audio/mp4", "mp3": "audio/mpeg",
          "mp4": "audio/mp4", "ogg": "audio/ogg"}.get(ext, "audio/wav")
    try:
        async with httpx.AsyncClient(timeout=60) as cl:
            r = await cl.post(STT_URL,
                headers={"api-subscription-key": settings.sarvam_api_key},
                files={"file": (filename, audio_bytes, ct)},
                data={"model": "saarika:v2.5", "language_code": code})
            if r.status_code != 200:
                return None
            return r.json().get("transcript")
    except Exception:
        return None
