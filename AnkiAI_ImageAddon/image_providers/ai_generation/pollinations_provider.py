"""
PollinationsProvider — GĐ5, Tier 5 (chốt chặn cuối cùng, §16)
================================================================
Stateless AI-image provider using the Pollinations.ai public endpoint.
No HTTP call is needed in search() — just construct URL deterministically.
The image is fetched on-demand by the consumer (Anki <img> tag).

Contract (MS §17.2):
  - Inherits BaseProvider
  - search() returns List[Candidate] synchronously
  - visual_type MUST be "metaphor_photo" (§6 only allows 7 types)
  - Reports to HealthBoard after every call
  - Checks QuotaManager before returning candidates
  - Returns [] on error — never raises/crashes
  - Tier 5 — only used when all other providers fail

Rate: ~50 req/hr (unofficial). License: CC-BY. Score: 0.6
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
# PollinationsProvider
# ---------------------------------------------------------------------------

# Prompt templates per visual_type (only metaphor_photo is supported)
_PROMPT_TEMPLATES = {
    "metaphor_photo": (
        "{query} metaphor: simple visual representation, "
        "educational flashcard, minimalist style, clear concept"
    ),
}


class PollinationsProvider(BaseProvider):
    """Stateless AI-image provider via Pollinations.ai URL construction.

    No HTTP request is made in search(); the returned URLs are consumed
    lazily by the Anki media import pipeline.  We still report to
    HealthBoard and QuotaManager for observability.
    """

    name = "pollinations"

    # Tier-5 supported visual types
    VISUAL_TYPES = ["metaphor_photo"]

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._base_url: str = cfg.get(
            "pollinations_base_url",
            "https://image.pollinations.ai/prompt",
        )
        self._width: int = int(cfg.get("ai_image_width", 512))
        self._height: int = int(cfg.get("ai_image_height", 512))
        self._timeout: float = float(cfg.get("provider_timeout_s", 15))
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
        """Construct Pollinations.ai image URLs for the query.

        No HTTP request is issued — only URL construction.
        Returns up to *limit* candidates with deterministic seeds.
        """
        t0 = time.perf_counter()

        # --- Guard: visual_type -------------------------------------------
        if visual_type not in self.VISUAL_TYPES:
            logger.debug(
                f"PollinationsProvider: visual_type '{visual_type}' not supported; skipping"
            )
            _get_health().report(self.name, time.perf_counter() - t0, ok=True)
            return []

        # --- QuotaManager check -------------------------------------------
        qm = _get_quota()
        _ensure_quota_bucket(qm, "pollinations", rpd=1200, rpm=50, tpm=0)
        if not qm.allow("pollinations"):
            logger.warning("PollinationsProvider: quota exhausted — skipping")
            _get_health().report(self.name, time.perf_counter() - t0, ok=False)
            return []

        # --- Build candidates ---------------------------------------------
        try:
            candidates = self._build_candidates(query, visual_type, limit)
        except Exception:
            logger.exception("PollinationsProvider: unexpected error building URLs")
            _get_health().report(self.name, time.perf_counter() - t0, ok=False)
            return []

        # --- Record quota & health ----------------------------------------
        for _ in candidates:
            qm.record("pollinations")

        latency = time.perf_counter() - t0
        _get_health().report(self.name, latency, ok=True)
        logger.debug(
            f"PollinationsProvider: built {len(candidates)} candidate(s) "
            f"in {latency:.4f}s for query='{query}'"
        )
        return candidates

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_candidates(
        self,
        query: str,
        visual_type: str,
        limit: int,
    ) -> List[Candidate]:
        """Construct candidate URLs with deterministic seeds."""
        template = _PROMPT_TEMPLATES.get(visual_type, _PROMPT_TEMPLATES["metaphor_photo"])
        prompt = template.format(query=query)

        candidates: List[Candidate] = []
        for i in range(limit):
            seed = hash(query) + i
            # Ensure seed is a non-negative integer for URL stability
            seed = seed if seed >= 0 else abs(seed)

            url = (
                f"{self._base_url}/{quote(prompt, safe='')}"
                f"?width={self._width}&height={self._height}"
                f"&seed={seed}&nologo=true"
            )

            cand = Candidate(
                url=url,
                provider=self.name,
                visual_type="metaphor_photo",  # ALWAYS metaphor_photo, never ai_generated
                width=self._width,
                height=self._height,
                license="CC-BY",
                attribution="Pollinations.ai",
                title=f"{query} (metaphor #{i + 1})",
                score=0.6,
            )
            candidates.append(cand)

        return candidates
