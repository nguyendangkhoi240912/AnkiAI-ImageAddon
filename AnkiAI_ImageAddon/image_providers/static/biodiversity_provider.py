"""Biodiversity Heritage Library image provider for AnkiAI ImageAddon.

Endpoint: https://www.biodiversitylibrary.org/api/v3/Search/{query}

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


class BiodiversityProvider(BaseProvider):
    """Fetch public-domain images from the Biodiversity Heritage Library."""

    name = "biodiversity"

    SUPPORTED_VISUAL_TYPES = {"photo", "diagram_or_map"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.api_base = cfg.get(
            "bhl_api_base", "https://www.biodiversitylibrary.org/api/v3"
        )
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
        """Search BHL for images matching *query*.

        Args:
            query: Search term (e.g. "orchid", "anatomy diagram").
            visual_type: Desired visual type; "photo" and "diagram_or_map" are served.
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
            results = self._do_search(query, visual_type, limit)
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

    def _do_search(self, query: str, visual_type: str, limit: int) -> List[Candidate]:
        """Search BHL API and extract image URLs from results.

        BHL v3 API returns search results with references to items/titles.
        Each item may have associated page images served via IIIF or direct URLs.
        """
        params: Dict[str, Any] = {
            "q": query,
            "page": 1,
            "pageSize": min(limit, 100),
            "format": "json",
        }

        resp = self.session.get(
            f"{self.api_base}/Search/{query}",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # BHL v3 search response structure
        results = data.get("Result", []) or data.get("results", [])

        if not results:
            return []

        candidates: List[Candidate] = []
        for item in results[:limit]:
            candidate = self._extract_candidate(item, visual_type)
            if candidate:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break

        return candidates

    def _extract_candidate(
        self, item: Dict[str, Any], visual_type: str
    ) -> Candidate | None:
        """Extract a Candidate from a single BHL search result item.

        BHL items can have:
          - ThumbnailUrl: direct thumbnail image link
          - IIIF manifest: for IIIF image construction
          - ItemUrl: link to the item page (for browsing)
        """
        # Try thumbnail URL first
        image_url = item.get("ThumbnailUrl", "") or item.get("thumbnailUrl", "")

        if not image_url:
            # Some results provide a direct image URL
            image_url = item.get("ImageUrl", "") or item.get("imageUrl", "")

        if not image_url:
            # Try to construct from item ID if available
            item_id = item.get("ItemID", "") or item.get("ItemId", "")
            page_id = item.get("PageID", "") or item.get("PageId", "")

            if page_id:
                # BHL page image URL pattern
                image_url = (
                    f"https://www.biodiversitylibrary.org/pageimage/{page_id}"
                )
            elif item_id:
                image_url = (
                    f"https://www.biodiversitylibrary.org/item/{item_id}"
                )

        if not image_url:
            return None

        title = (
            item.get("Title", "")
            or item.get("FullTitle", "")
            or item.get("title", "")
        )

        # Attribution
        contributors = item.get("Contributor", []) or []
        if isinstance(contributors, list) and contributors:
            contributor_str = contributors[0] if isinstance(contributors[0], str) else str(contributors[0])
        else:
            contributor_str = ""

        attribution = "Biodiversity Heritage Library / Public Domain"
        if contributor_str:
            attribution = f"{contributor_str} / BHL / Public Domain"

        return Candidate(
            url=image_url,
            provider=self.name,
            visual_type=visual_type,
            width=0,
            height=0,
            license="Public Domain",
            attribution=attribution,
            title=title,
            score=0.55,
        )
