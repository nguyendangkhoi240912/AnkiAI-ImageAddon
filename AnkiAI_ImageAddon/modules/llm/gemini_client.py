"""
Gemini Client — GĐ4, G4.2                                  [MS §4]
=========================================================================
Text backup + Vision QC xương sống.

Vai trò:
  • Text: dự phòng khi Groq hết quota / model bị rút
  • Vision QC: gọi đồng bộ, là bước chính xác thực ảnh (P3)

Không import Qt/Anki.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from AnkiAI_ImageAddon.modules.http_session_manager import HTTPSessionManager

logger = logging.getLogger(__name__)

_GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_DEFAULT_TEXT_MODEL = "gemini-2.0-flash-lite"
_DEFAULT_VISION_MODEL = "gemini-2.0-flash-lite"
_DEFAULT_TEMPERATURE = 0.3
_DEFAULT_MAX_TOKENS = 512


class GeminiError(Exception):
    pass


class GeminiClient:
    """
    Thin Gemini REST client for text and vision tasks.

    Args:
        api_keys:      List of API keys (auto-failover on 429).
        text_model:    Model for text-only calls.
        vision_model:  Model for vision QC calls (must support image input).
        timeout_s:     Default request timeout.
    """

    def __init__(
        self,
        api_keys: List[str],
        text_model: str = _DEFAULT_TEXT_MODEL,
        vision_model: str = _DEFAULT_VISION_MODEL,
        timeout_s: float = 15.0,
    ):
        keys = [k.strip() for k in api_keys if k and k.strip()]
        if not keys:
            raise GeminiError("No Gemini API keys configured")
        self._keys = keys
        self._key_index = 0
        self._text_model = text_model
        self._vision_model = vision_model
        self._timeout_s = timeout_s
        self._session = HTTPSessionManager.get_session("gemini_llm")
        # Probe results
        self._vision_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # API key rotation
    # ------------------------------------------------------------------

    def _next_key(self) -> str:
        key = self._keys[self._key_index % len(self._keys)]
        self._key_index += 1
        return key

    # ------------------------------------------------------------------
    # Core call
    # ------------------------------------------------------------------

    def _call(
        self,
        model: str,
        contents: List[Dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
        timeout_s: Optional[float] = None,
    ) -> str:
        """Call Gemini generateContent; return text. Tries all keys on 429."""
        if timeout_s is None:
            timeout_s = self._timeout_s

        url = _GEMINI_GENERATE_URL.format(model=model)
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        for attempt in range(len(self._keys)):
            key = self._next_key()
            try:
                resp = self._session.post(
                    url,
                    params={"key": key},
                    json=payload,
                    timeout=timeout_s,
                )
                if resp.status_code == 429:
                    logger.debug(f"Gemini 429 on key index {(self._key_index - 1) % len(self._keys)}, trying next key")
                    continue
                if resp.status_code == 404:
                    raise GeminiError(f"Gemini model not found: {model}")
                if resp.status_code != 200:
                    raise GeminiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                if not text:
                    raise GeminiError("Empty response from Gemini")
                return text
            except requests.exceptions.Timeout:
                raise GeminiError(f"Gemini timeout ({timeout_s}s)")
            except requests.exceptions.ConnectionError as e:
                raise GeminiError(f"Gemini connection error: {e}")
            except GeminiError:
                raise

        raise GeminiError("All Gemini API keys exhausted (all returned 429)")

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    def generate_text(
        self,
        system: str,
        user: str,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        timeout_s: Optional[float] = None,
    ) -> str:
        """Text-only generation (backup for Groq)."""
        contents = [
            {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}
        ]
        return self._call(
            model=self._text_model,
            contents=contents,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
        )

    def classify_batch(self, items: List[dict], timeout_s: Optional[float] = None) -> list:
        """P1 batch via Gemini (text backup). Returns list of verdict dicts."""
        from AnkiAI_ImageAddon.modules.llm.prompts import (
            P1_SYSTEM, build_p1_user, parse_p1_response,
        )
        text = self.generate_text(
            system=P1_SYSTEM,
            user=build_p1_user(items),
            timeout_s=timeout_s,
        )
        result = parse_p1_response(text)
        if not result:
            # Retry once
            text2 = self.generate_text(P1_SYSTEM, build_p1_user(items), timeout_s=timeout_s)
            result = parse_p1_response(text2)
        return result

    # ------------------------------------------------------------------
    # Vision QC (P3) — synchronous, core to pipeline
    # ------------------------------------------------------------------

    def vision_qc_batch(
        self,
        pairs: List[dict],
        timeout_s: Optional[float] = None,
    ) -> list:
        """Run P3 vision QC on a batch of (word, image_url) pairs.

        Args:
            pairs: List of {i, word, sense, group, image_url} dicts.
            timeout_s: Override default timeout.

        Returns:
            List of {i, ok, r} dicts. Empty list on total failure.
        """
        from AnkiAI_ImageAddon.modules.llm.prompts import (
            P3_SYSTEM, build_p3_user, parse_p3_response,
        )
        if timeout_s is None:
            timeout_s = self._timeout_s

        # Build contents with text prompt + inline image URLs
        # Gemini supports image_url via parts[].inlineData or via URL fetch
        # Using URL-based approach (no binary download needed on our side)
        user_text = build_p3_user(pairs)

        # Include image URLs as inline parts for vision model
        parts: List[Dict] = [{"text": f"{P3_SYSTEM}\n\n{user_text}"}]

        # Add image parts for each pair (Gemini will fetch URLs)
        for pair in pairs:
            url = pair.get("image_url", "")
            if url and not url.startswith("data:"):
                parts.append({
                    "fileData": {
                        "mimeType": "image/jpeg",
                        "fileUri": url,
                    }
                })

        contents = [{"role": "user", "parts": parts}]

        try:
            text = self._call(
                model=self._vision_model,
                contents=contents,
                max_tokens=256,
                timeout_s=timeout_s,
            )
            result = parse_p3_response(text)
            if result:
                return result
            # Retry once with text-only fallback (without images)
            text2 = self._call(
                model=self._vision_model,
                contents=[{"role": "user", "parts": [{"text": f"{P3_SYSTEM}\n\n{user_text}"}]}],
                max_tokens=256,
                timeout_s=timeout_s,
            )
            return parse_p3_response(text2)
        except GeminiError as e:
            logger.warning(f"Vision QC failed: {e}")
            return []

    def probe_vision(self, timeout_s: float = 5.0) -> bool:
        """Check if vision model is available. Caches result."""
        if self._vision_available is not None:
            return self._vision_available
        try:
            contents = [{"role": "user", "parts": [{"text": "Reply with 1 if you can see images."}]}]
            self._call(self._vision_model, contents, max_tokens=5, timeout_s=timeout_s)
            self._vision_available = True
        except GeminiError:
            self._vision_available = False
        logger.info(f"Gemini vision probe: {'✓' if self._vision_available else '✗'} {self._vision_model}")
        return bool(self._vision_available)


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_global_client: Optional[GeminiClient] = None


def get_gemini_client(config=None) -> Optional[GeminiClient]:
    """Lazy singleton. Returns None if no API keys configured."""
    global _global_client
    if _global_client is not None:
        return _global_client
    if config is None:
        try:
            from AnkiAI_ImageAddon.modules.config import get_config_manager
            config = get_config_manager()
        except Exception:
            return None

    # Gather all eval/vision keys
    keys = [config.get(f"gemini_eval_api_key_{i}", "") for i in range(1, 8)]
    keys += [config.get("gemini_api_key", ""), config.get("gemini_backup_api_key", "")]
    keys = [k for k in keys if k and k.strip()]
    if not keys:
        return None

    _global_client = GeminiClient(
        api_keys=keys,
        text_model=config.get("gemini_vision_model", _DEFAULT_TEXT_MODEL),
        vision_model=config.get("gemini_vision_model", _DEFAULT_VISION_MODEL),
    )
    return _global_client
