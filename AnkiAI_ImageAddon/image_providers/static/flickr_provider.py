"""Flickr CC image provider for AnkiAI ImageAddon.

Endpoint: https://api.flickr.com/services/rest/?method=flickr.photos.search
Filters CC licenses only: license=4,5,6,7,9,10 + safe_search=1

License: CC-BY / CC-BY-SA / CC-BY-NC (varies per photo)
Rate limit: 3600 req/hr

Name: "flickr_cc" (avoids clash with existing legacy FlickrProvider).
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


# CC license IDs on Flickr:
#   4  = CC-BY
#   5  = CC-BY-SA
#   6  = CC-BY-NC
#   7  = CC-BY-ND       (included for coverage, though ND restricts derivatives)
#   9  = CC0
#  10  = Public Domain Mark
_CC_LICENSE_IDS = "4,5,6,7,9,10"

# Mapping from Flickr license ID to short label
_LICENSE_MAP: Dict[int, str] = {
    4: "CC-BY",
    5: "CC-BY-SA",
    6: "CC-BY-NC",
    7: "CC-BY-ND",
    9: "CC0",
    10: "Public Domain",
}


class NewFlickrProvider(BaseProvider):
    """Fetch Creative Commons–licensed images from Flickr."""

    name = "flickr_cc"

    SUPPORTED_VISUAL_TYPES = {"photo"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.api_key = cfg.get("flickr_api_key", "")
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
        """Search Flickr for CC-licensed photos matching *query*.

        Args:
            query: Search term (e.g. "sunset beach").
            visual_type: Desired visual type; only "photo" is served.
            limit: Maximum candidates to return.

        Returns:
            List[Candidate] — may be empty on error or no results.
        """
        if visual_type not in self.SUPPORTED_VISUAL_TYPES:
            return []

        # Flickr requires an API key
        if not self.api_key:
            logger.info(f"[{self.name}] no API key configured — skipping")
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
        """Search Flickr API and construct image URLs."""
        params: Dict[str, Any] = {
            "method": "flickr.photos.search",
            "api_key": self.api_key,
            "text": query,
            "license": _CC_LICENSE_IDS,
            "safe_search": 1,
            "content_type": 1,          # photos only (1=photos, 2=screens, 4=other)
            "sort": "relevance",
            "per_page": min(limit, 500),
            "format": "json",
            "nojsoncallback": 1,
            "extras": "license,owner_name,url_z,url_o",
        }

        resp = self.session.get(
            "https://api.flickr.com/services/rest/",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Check for API-level errors
        if data.get("stat") != "ok":
            err_msg = data.get("message", "unknown error")
            logger.warning(f"[{self.name}] Flickr API error: {err_msg}")
            return []

        photos = data.get("photos", {}).get("photo", [])
        if not photos:
            return []

        candidates: List[Candidate] = []
        for photo in photos[:limit]:
            candidate = self._photo_to_candidate(photo)
            if candidate:
                candidates.append(candidate)

        return candidates

    def _photo_to_candidate(self, photo: Dict[str, Any]) -> Candidate | None:
        """Convert a Flickr photo dict to a Candidate."""
        # Prefer pre-constructed URL from extras, else build manually
        image_url = photo.get("url_z", "") or photo.get("url_o", "")

        if not image_url:
            # Build URL manually: https://farm{farm}.staticflickr.com/{server}/{id}_{secret}_z.jpg
            farm = photo.get("farm", "")
            server = photo.get("server", "")
            photo_id = photo.get("id", "")
            secret = photo.get("secret", "")

            if not all([farm, server, photo_id, secret]):
                return None

            image_url = (
                f"https://farm{farm}.staticflickr.com/{server}/{photo_id}_{secret}_z.jpg"
            )

        # License
        license_id = int(photo.get("license", 0))
        license_label = _LICENSE_MAP.get(license_id, "CC")

        # Attribution
        owner_name = photo.get("ownername", "") or photo.get("owner", "")
        title = photo.get("title", "")

        attribution = f"{owner_name} / Flickr / {license_label}" if owner_name else f"Flickr / {license_label}"

        return Candidate(
            url=image_url,
            provider=self.name,
            visual_type="photo",
            width=0,
            height=0,
            license=license_label,
            attribution=attribution,
            title=title,
            score=0.55,
        )
