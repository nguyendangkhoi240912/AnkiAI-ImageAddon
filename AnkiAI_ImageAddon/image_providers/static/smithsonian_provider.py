"""Smithsonian Institution image provider for AnkiAI ImageAddon.

Endpoint: https://api.si.edu/v1/search
License: Public Domain
Rate limit: 1000 req/day
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Any

import requests

from ..base_provider import BaseProvider, Candidate

logger = logging.getLogger(__name__)


def _get_health():
    from ..health import get_health_board
    return get_health_board()


def _get_quota():
    from ...modules.quota import get_quota_manager
    return get_quota_manager()


class SmithsonianProvider(BaseProvider):
    """Fetch public-domain images from the Smithsonian Open Access API."""

    name = "smithsonian"

    SUPPORTED_VISUAL_TYPES = {"photo"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.api_base = cfg.get(
            "smithsonian_api_base", "https://api.si.edu/v1"
        )
        self.api_key = cfg.get("smithsonian_api_key", "")
        self.timeout = cfg.get("provider_timeout_s", 10)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AnkiAI-ImageAddon/5.1 (https://github.com/ankiai; educational use)"
        })

    def search(
        self,
        query: str,
        visual_type: str = "photo",
        limit: int = 10,
    ) -> List[Candidate]:
        """Search Smithsonian collections for images matching *query*.

        Args:
            query: Search term (e.g. "butterfly").
            visual_type: Desired visual type; only "photo" is served.
            limit: Maximum candidates to return.

        Returns:
            List[Candidate] — may be empty on error or no results.
        """
        if visual_type not in self.SUPPORTED_VISUAL_TYPES:
            return []

        quota = _get_quota()
        if not quota.allow(self.name):
            logger.info(f"[{self.name}] quota exhausted — skipping")
            return []

        t0 = time.perf_counter()
        ok = False
        try:
            results = self._do_search(query, limit)
            ok = True
            return results
        except Exception as exc:
            logger.warning(f"[{self.name}] search error: {exc}", exc_info=True)
            return []
        finally:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=ok)
            if ok:
                quota.record(self.name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _do_search(self, query: str, limit: int) -> List[Candidate]:
        """Search the Smithsonian API and extract image URLs from rows."""
        params: Dict[str, Any] = {
            "q": query,
            "rows": min(limit, 100),
            "start": 0,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        resp = self.session.get(
            f"{self.api_base}/search",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        rows = data.get("rows", [])
        if not rows:
            return []

        candidates: List[Candidate] = []
        for row in rows[:limit]:
            candidate = self._extract_candidate(row)
            if candidate:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break

        return candidates

    def _extract_candidate(self, row: Dict[str, Any]) -> Candidate | None:
        """Extract a Candidate from a single Smithsonian API row.

        The Smithsonian Open Access API returns rows with a
        ``content`` dict containing ``media`` → list of media objects,
        each with ``thumbnail`` or ``url`` fields.
        """
        # Title
        title = row.get("title", "") or ""

        # Extract image URL from content.media
        content = row.get("content", {})
        media_list = content.get("media", [])

        image_url = None
        for media in media_list:
            # Prefer thumbnail (guaranteed image), fallback to url
            thumbnail = media.get("thumbnail", "")
            if thumbnail:
                image_url = thumbnail
                break
            url = media.get("url", "")
            if url:
                image_url = url
                break

        if not image_url:
            # Some rows put images directly in content.images
            images = content.get("images", [])
            for img in images:
                img_url = img.get("url", "") or img.get("thumbnail", "")
                if img_url:
                    image_url = img_url
                    break

        if not image_url:
            return None

        # Attribution: unit_code (e.g. "NMNH") identifies the museum
        unit_code = row.get("unit_code", "")
        attribution = "Smithsonian Institution / Public Domain"
        if unit_code:
            attribution = f"Smithsonian ({unit_code}) / Public Domain"

        return Candidate(
            url=image_url,
            provider=self.name,
            visual_type="photo",
            width=0,
            height=0,
            license="Public Domain",
            attribution=attribution,
            title=title,
            score=0.6,
        )
