"""Traduction via l'API compatible OpenAI (worker Cloudflare)."""
from __future__ import annotations

import html

import httpx

from .config import settings


async def translate(text: str, source: str, target: str) -> str | None:
    if not text or not settings.translate_api_url or source == target:
        return None
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.translate_api_key}",
    }
    payload = {
        "model": "google-translate",
        "messages": [{"role": "user", "content": text}],
        "source_lang": source, "target_lang": target, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=25) as cl:
            r = await cl.post(settings.translate_api_url, headers=headers, json=payload)
            if r.status_code != 200:
                return None
            data = r.json()
            out = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content")
            return html.unescape(out) if out else None
    except Exception:
        return None
