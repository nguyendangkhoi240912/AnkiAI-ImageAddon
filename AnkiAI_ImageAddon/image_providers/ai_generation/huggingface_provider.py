"""
HuggingFaceProvider — GĐ5, Tier 5 (chốt chặn cuối cùng, §16)
================================================================
AI-image provider using the HuggingFace Inference API (Stable Diffusion).
Makes a real HTTP POST to generate an image, then saves the binary
response to a local cache and returns a file:// URL.

Contract (MS §17.2):
  - Inherits BaseProvider
  - search() returns List[Candidate] synchronously (requests.Session, NO asyncio)
  - visual_type MUST be "metaphor_photo" (§6 only allows 7 types)
  - Reports to HealthBoard after every call
  - Checks QuotaManager STRICTLY before API calls (rpd=50)
  - Returns [] on error — never raises/crashes
  - Tier 5 — only used when all other providers fail

Rate: ~1000 req/month (very tight free tier). License: CC-BY. Score: 0.5
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any, Dict, List
from urllib.parse import quote

import requests

from ..base_provider import BaseProvider, Candidate

logger = logging.getLogger(__name__)

USER_FILES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_files",
)

# Sub-directory for cached HF images
_HF_CACHE_DIR = os.path.join(USER_FILES, "hf_cache")

# ---------------------------------------------------------------------------
# Lazy singletons for HealthBoard and QuotaManager
# ---------------------------------------------------------------------------


def _get_health():
    from ..health import get_health_board
    return get_health_board()


def _get_quota():
    from ...modules.quota import get_quota_manager
    return get_quota_manager()


def _ensure_quota_bucket(qm, name: str, rpd: int, rpm: int, tpm: int = 0) -> None:
    """Register a model bucket in the QuotaManager if not already present."""
    if name in qm._buckets:
        return
    with qm._lock:
        if name not in qm._buckets:
            from ...modules.quota import _ModelBucket
            qm._buckets[name] = _ModelBucket(
                rpd_limit=rpd, rpm_limit=rpm, tpm_limit=tpm,
            )
            logger.debug(f"QuotaManager: registered bucket '{name}' rpd={rpd} rpm={rpm}")


# ---------------------------------------------------------------------------
# HuggingFaceProvider
# ---------------------------------------------------------------------------

# Prompt template (only metaphor_photo supported)
_PROMPT_TEMPLATE = (
    "{query} metaphor: simple visual, educational flashcard, "
    "minimalist, clear concept, high quality"
)


class HuggingFaceProvider(BaseProvider):
    """AI-image provider via HuggingFace Inference API.

    Generates images using Stable Diffusion, saves binary response to
    ``user_files/hf_cache/<hash>.jpg``, and returns a ``file://`` URL.
    """

    name = "huggingface"

    # Tier-5 supported visual types
    VISUAL_TYPES = ["metaphor_photo"]

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._api_token: str = cfg.get("huggingface_api_token", "")
        self._model: str = cfg.get(
            "huggingface_model",
            "stabilityai/stable-diffusion-xl-base-1.0",
        )
        self._width: int = int(cfg.get("ai_image_width", 512))
        self._height: int = int(cfg.get("ai_image_height", 512))
        self._timeout: float = float(cfg.get("provider_timeout_s", 30))
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        visual_type: str = "metaphor_photo",
        limit: int = 10,
    ) -> List[Candidate]:
        """Generate an AI image via HuggingFace and return a cached local path.

        Only 1 candidate is returned per call (image generation is expensive).
        The *limit* parameter is capped at 1 internally.
        """
        t0 = time.perf_counter()

        # --- Guard: visual_type -------------------------------------------
        if visual_type not in self.VISUAL_TYPES:
            logger.debug(
                f"HuggingFaceProvider: visual_type '{visual_type}' not supported; skipping"
            )
            _get_health().report(self.name, time.perf_counter() - t0, ok=True)
            return []

        # --- Guard: API token required ------------------------------------
        if not self._api_token:
            logger.warning(
                "HuggingFaceProvider: no API token configured "
                "(huggingface_api_token) — skipping"
            )
            _get_health().report(self.name, time.perf_counter() - t0, ok=False)
            return []

        # --- QuotaManager STRICT check (rpd=50) --------------------------
        qm = _get_quota()
        _ensure_quota_bucket(qm, "huggingface", rpd=50, rpm=10, tpm=0)
        if not qm.allow("huggingface"):
            logger.warning("HuggingFaceProvider: quota exhausted — skipping")
            _get_health().report(self.name, time.perf_counter() - t0, ok=False)
            return []

        # --- Build prompt & call API --------------------------------------
        prompt = _PROMPT_TEMPLATE.format(query=query)
        candidates: List[Candidate] = []

        try:
            image_bytes = self._call_api(prompt)
            if image_bytes:
                local_url = self._save_to_cache(query, prompt, image_bytes)
                if local_url:
                    candidates.append(
                        Candidate(
                            url=local_url,
                            provider=self.name,
                            visual_type="metaphor_photo",  # ALWAYS metaphor_photo
                            width=self._width,
                            height=self._height,
                            license="CC-BY",
                            attribution=f"HuggingFace ({self._model})",
                            title=f"{query} (AI metaphor)",
                            score=0.5,
                        )
                    )
                    qm.record("huggingface")
        except Exception:
            logger.exception("HuggingFaceProvider: unexpected error during generation")
            _get_health().report(self.name, time.perf_counter() - t0, ok=False)
            return []

        latency = time.perf_counter() - t0
        ok = len(candidates) > 0
        _get_health().report(self.name, latency, ok=ok)
        logger.debug(
            f"HuggingFaceProvider: {'generated' if ok else 'failed'} "
            f"in {latency:.2f}s for query='{query}'"
        )
        return candidates

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_api(self, prompt: str) -> bytes | None:
        """POST to HuggingFace Inference API and return raw image bytes.

        Returns None on any error (logged, not raised).
        """
        url = f"https://api-inference.huggingface.co/models/{self._model}"
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }
        payload = {"inputs": prompt}

        try:
            resp = self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")
            if "image" not in content_type and not resp.content[:4] in (
                b"\x89PNG",
                b"\xff\xd8\xff",  # JPEG
            ):
                # HF sometimes returns JSON errors even with 200 status
                logger.warning(
                    f"HuggingFaceProvider: unexpected content type '{content_type}' "
                    f"— response may not be an image"
                )
                # Try to detect if it's a JSON error payload
                try:
                    err = resp.json()
                    logger.warning(f"HuggingFaceProvider: API error payload: {err}")
                except Exception:
                    pass
                return None

            return resp.content

        except requests.exceptions.Timeout:
            logger.warning(
                f"HuggingFaceProvider: request timed out ({self._timeout}s)"
            )
            return None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            logger.warning(f"HuggingFaceProvider: HTTP {status} — {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"HuggingFaceProvider: network error — {e}")
            return None

    def _save_to_cache(self, query: str, prompt: str, image_bytes: bytes) -> str | None:
        """Save image bytes to user_files/hf_cache/ and return a file:// URL.

        File name is derived from a hash of query + prompt for deterministic
        caching (identical inputs produce the same file path).
        """
        try:
            os.makedirs(_HF_CACHE_DIR, exist_ok=True)
        except OSError:
            logger.exception("HuggingFaceProvider: cannot create cache directory")
            return None

        # Deterministic filename — same query+prompt always maps to same file
        content_hash = hashlib.sha256(
            f"{query}||{prompt}".encode("utf-8")
        ).hexdigest()[:16]
        filename = f"{content_hash}.jpg"
        filepath = os.path.join(_HF_CACHE_DIR, filename)

        try:
            with open(filepath, "wb") as f:
                f.write(image_bytes)
        except OSError:
            logger.exception(f"HuggingFaceProvider: cannot write cache file {filepath}")
            return None

        # Return absolute file:// URL for Anki media pipeline
        abs_path = os.path.abspath(filepath)
        return f"file://{abs_path}"
