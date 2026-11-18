"""
llm.py — Thin wrapper around Google Gemini (google-genai SDK).

Every AI feature in the app checks `llm.available` first and has a deterministic
local fallback, so the platform works end-to-end without an API key.
"""

import asyncio
import json
import logging
import re
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiLLM:
    def __init__(self):
        self._client = None
        self._failed = False

    @property
    def available(self) -> bool:
        return bool(settings.GEMINI_API_KEY) and not self._failed

    @property
    def model_name(self) -> str:
        return settings.GEMINI_MODEL

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _generate_sync(self, prompt: str, as_json: bool, temperature: float) -> str:
        config: dict[str, Any] = {"temperature": temperature}
        if as_json:
            config["response_mime_type"] = "application/json"
        resp = self._get_client().models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt, config=config
        )
        return resp.text or ""

    async def generate(self, prompt: str, temperature: float = 0.2) -> Optional[str]:
        if not self.available:
            return None
        try:
            return await asyncio.to_thread(self._generate_sync, prompt, False, temperature)
        except Exception as e:
            logger.error("Gemini call failed: %s", e)
            return None

    async def generate_json(self, prompt: str, temperature: float = 0.1) -> Optional[Any]:
        if not self.available:
            return None
        try:
            raw = await asyncio.to_thread(self._generate_sync, prompt, True, temperature)
            raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
            return json.loads(raw)
        except Exception as e:
            logger.error("Gemini JSON call failed: %s", e)
            return None


llm = GeminiLLM()
