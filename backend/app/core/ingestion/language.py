"""
language.py — Language detection and translation (USP 4: bilingual English + Malayalam).

Detection: Unicode-script check first (Malayalam block U+0D00–U+0D7F is unambiguous),
then langdetect for everything else.
Translation: Google Translate (deep-translator) → Gemini → passthrough.
"""

import asyncio
import logging
from typing import Optional

from app.config import settings
from app.core.agents.llm import llm

logger = logging.getLogger(__name__)

LANG_NAMES = {"en": "English", "ml": "Malayalam", "hi": "Hindi", "ta": "Tamil"}


def malayalam_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    ml = sum(1 for c in letters if "ഀ" <= c <= "ൿ")
    return ml / len(letters)


def detect_language(text: str) -> str:
    sample = (text or "")[:5000]
    if not sample.strip():
        return "en"
    if malayalam_ratio(sample) > 0.3:
        return "ml"
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        return detect(sample)
    except Exception:
        return "en"


GOOGLE_URL = "https://translate.googleapis.com/translate_a/single"


def _google_translate(text: str, source: str, target: str) -> str:
    """Google's public translate endpoint (no key). Sent in ~3,500-char slices on paragraph boundaries.
    Uses urllib on purpose: the endpoint rate-limits some HTTP client fingerprints (e.g. httpx) outright."""
    import json
    import urllib.parse
    import urllib.request

    slices, buf = [], ""
    for para in text.split("\n"):
        if len(buf) + len(para) > 3500 and buf:
            slices.append(buf)
            buf = ""
        buf += para + "\n"
    if buf.strip():
        slices.append(buf)

    url = GOOGLE_URL + "?" + urllib.parse.urlencode({"client": "gtx", "sl": source, "tl": target, "dt": "t"})
    out = []
    for chunk in slices:
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode({"q": chunk}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read())
        out.append("".join(seg[0] for seg in payload[0] if seg and seg[0]))
    return "".join(out).strip()


async def translate(text: str, source: str, target: str) -> tuple[str, Optional[str]]:
    """Returns (translated_text, engine_used). engine_used is None if nothing worked."""
    if not text.strip() or source == target:
        return text, "none"

    if settings.TRANSLATOR in ("google", "auto"):
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_google_translate, text, source, target), timeout=20
            )
            if result:
                return result, "google-translate"
        except Exception as e:
            logger.warning("Google translate failed (%s), trying Gemini", e)

    if llm.available and settings.TRANSLATOR != "none":
        prompt = (
            f"Translate the following text from {LANG_NAMES.get(source, source)} to "
            f"{LANG_NAMES.get(target, target)}. Return only the translation.\n\n{text}"
        )
        result = await llm.generate(prompt, temperature=0)
        if result:
            return result.strip(), "gemini"

    return text, None
