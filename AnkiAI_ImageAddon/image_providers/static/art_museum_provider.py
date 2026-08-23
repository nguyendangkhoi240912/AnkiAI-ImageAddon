"""Art Museum image provider for AnkiAI ImageAddon.

Combined provider: Art Institute of Chicago + Cleveland Museum of Art.

  - Art Institute Chicago: https://api.artic.edu/api/v1/artworks/search
  - Cleveland Museum: https://openaccess-api.clevelandart.org/api/artworks/

License: Public Domain / CC0
Rate limit: ~1000 req/hr each
"""

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


class ArtMuseumProvider(BaseProvider):
    """Fetch public-domain artwork images from Art Institute Chicago
    and Cleveland Museum of Art."""

    name = "artic"  # primary; also serves as "cleveland" sub-provider

    SUPPORTED_VISUAL_TYPES = {"photo"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.artic_api_base = cfg.get(
            "artic_api_base", "https://api.artic.edu/api/v1"
        )
        self.cleveland_api_base = cfg.get(
            "cleveland_api_base", "https://openaccess-api.clevelandart.org/api"
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
        """Search both Art Institute Chicago and Cleveland Museum of Art.

        Merges and deduplicates results from both sub-providers.

        Args:
            query: Search term (e.g. "Monet water lilies").
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
            # Search both sub-providers and merge
            artic_results = self._search_artic(query, limit)
            cleveland_results = self._search_cleveland(query, limit)

            merged = artic_results + cleveland_results

            # Deduplicate by URL
            seen_urls: set[str] = set()
            unique: List[Candidate] = []
            for c in merged:
                if c.url not in seen_urls:
                    seen_urls.add(c.url)
                    unique.append(c)
                if len(unique) >= limit:
                    break

            ok = True
            return unique
        except Exception as exc:
            logger.warning(f"[{self.name}] search error: {exc}", exc_info=True)
            return []
        finally:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=ok)
            if ok:
                quota.record(self.name)

    # ------------------------------------------------------------------
    # Art Institute of Chicago
    # ------------------------------------------------------------------

    def _search_artic(self, query: str, limit: int) -> List[Candidate]:
        """Search Art Institute Chicago API."""
        try:
            params = {
                "q": query,
                "limit": min(limit, 100),
                "fields": "id,title,image_id,artist_display,license_type",
            }
            resp = self.session.get(
                f"{self.artic_api_base}/artworks/search",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.debug(f"[{self.name}] Artic search failed: {exc}")
            return []

        artworks = data.get("data", [])
        candidates: List[Candidate] = []

        for artwork in artworks:
            image_id = artwork.get("image_id", "")
            if not image_id:
                continue

            # Artic IIIF image URL pattern
            image_url = (
                f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
            )

            title = artwork.get("title", "")
            artist = artwork.get("artist_display", "")
            attribution = "Art Institute of Chicago / Public Domain"
            if artist:
                attribution = f"{artist} — Art Institute of Chicago / Public Domain"

            candidates.append(Candidate(
                url=image_url,
                provider=self.name,
                visual_type="photo",
                width=843,
                height=0,
                license="Public Domain",
                attribution=attribution,
                title=title,
                score=0.65,
            ))

        return candidates[:limit]

    # ------------------------------------------------------------------
    # Cleveland Museum of Art
    # ------------------------------------------------------------------

    def _search_cleveland(self, query: str, limit: int) -> List[Candidate]:
        """Search Cleveland Museum of Art Open Access API."""
        try:
            params = {
                "q": query,
                "limit": min(limit, 100),
            }
            resp = self.session.get(
                f"{self.cleveland_api_base}/artworks/",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.debug(f"[{self.name}] Cleveland search failed: {exc}")
            return []

        # Cleveland API wraps results in "data" key
        artworks = data.get("data", [])
        candidates: List[Candidate] = []

        for artwork in artworks:
            # Cleveland provides images in multiple sizes; prefer web (larger)
            images = artwork.get("images", {})
            image_url = ""

            if isinstance(images, dict):
                web = images.get("web", {})
                image_url = web.get("url", "") if isinstance(web, dict) else ""

                if not image_url:
                    digital = images.get("digital", {})
                    image_url = (
                        digital.get("url", "") if isinstance(digital, dict) else ""
                    )

            if not image_url:
                # Fallback: some records put url directly
                image_url = artwork.get("url", "")

            if not image_url:
                continue

            title = artwork.get("title", "")
            creator = artwork.get("creators", [])
            creator_name = ""
            if isinstance(creator, list) and creator:
                creator_name = creator[0].get("description", "") if isinstance(creator[0], dict) else str(creator[0])

            attribution = "Cleveland Museum of Art / CC0"
            if creator_name:
                attribution = f"{creator_name} — Cleveland Museum of Art / CC0"

            # Cleveland uses accession_number for rights info
            rights = artwork.get("accession_number", "")

            candidates.append(Candidate(
                url=image_url,
                provider=self.name,
                visual_type="photo",
                width=0,
                height=0,
                license="CC0",
                attribution=attribution,
                title=title,
                score=0.6,
            ))

        return candidates[:limit]
