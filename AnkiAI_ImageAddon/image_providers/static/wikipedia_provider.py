"""Wikipedia image provider for AnkiAI ImageAddon.

2-step search:
  1. Search articles via MediaWiki API (action=query&list=search)
  2. Fetch lead image via REST summary API (/page/summary/{title})

License: CC-BY-SA-3.0
Rate limit: ~500 req/hr
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


class WikipediaProvider(BaseProvider):
    """Fetch lead images from Wikipedia articles."""

    name = "wikipedia"

    # Visual types this provider can serve
    SUPPORTED_VISUAL_TYPES = {"photo", "diagram_or_map"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.api_base = cfg.get("wikipedia_api_base", "https://en.wikipedia.org")
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
        """Search Wikipedia for article lead images matching *query*.

        Args:
            query: Search term (e.g. "mitochondria").
            visual_type: Desired visual type; only "photo" and "diagram_or_map" are served.
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
        """Step 1: search articles; Step 2: fetch lead image for each."""
        # --- Step 1: article search ---
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(limit, 50),
            "format": "json",
        }
        resp = self.session.get(
            f"{self.api_base}/w/api.php",
            params=search_params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        search_hits = data.get("query", {}).get("search", [])
        if not search_hits:
            return []

        # --- Step 2: fetch lead image for each article ---
        candidates: List[Candidate] = []
        for hit in search_hits[:limit]:
            title = hit.get("title", "")
            if not title:
                continue
            candidate = self._fetch_lead_image(title)
            if candidate:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break

        return candidates

    def _fetch_lead_image(self, title: str) -> Candidate | None:
        """Fetch the lead (thumbnail) image for a Wikipedia article title."""
        try:
            resp = self.session.get(
                f"{self.api_base}/api/rest_v1/page/summary/{title}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.debug(f"[{self.name}] summary fetch failed for '{title}': {exc}")
            return None

        thumbnail = data.get("thumbnail", {})
        image_url = thumbnail.get("source", "")
        if not image_url:
            return None

        # Try to upgrade from thumbnail to full-resolution original
        original_url = self._upgrade_to_original(image_url)

        article_title = data.get("title", title)
        description = data.get("description", "")
        attr_label = article_title
        if description:
            attr_label = f"{article_title} — {description}"

        return Candidate(
            url=original_url or image_url,
            provider=self.name,
            visual_type="photo",
            width=thumbnail.get("width", 0),
            height=thumbnail.get("height", 0),
            license="CC-BY-SA-3.0",
            attribution=f"Wikipedia / {attr_label} / CC-BY-SA-3.0",
            title=article_title,
            score=0.7,
        )

    @staticmethod
    def _upgrade_to_original(thumbnail_url: str) -> str:
        """Attempt to convert a thumbnail URL to the full-resolution original.

        Wikipedia thumbnail URLs look like:
          https://upload.wikimedia.org/.../thumb/FILENAME/WIDTHpx-FILENAME
        The original is:
          https://upload.wikimedia.org/.../FILENAME
        """
        if "/thumb/" not in thumbnail_url:
            return thumbnail_url

        # Remove "/thumb/" and the size prefix segment
        # e.g. .../thumb/File.png/220px-File.png → .../File.png
        parts = thumbnail_url.split("/thumb/")
        if len(parts) != 2:
            return thumbnail_url

        path_after_thumb = parts[1]  # e.g. "File.png/220px-File.png"
        segments = path_after_thumb.split("/")
        if len(segments) < 2:
            return thumbnail_url

        filename = segments[0]
        return f"{parts[0]}/{filename}"
