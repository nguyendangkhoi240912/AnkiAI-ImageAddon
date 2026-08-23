"""Wikidata image provider for AnkiAI ImageAddon.

3-step search:
  1. Search for entity QID via wbsearchentities
  2. Fetch entity data to get P18 (image) property
  3. Construct Commons URL from the image filename

License: CC0
Rate limit: 100 req/min
"""

from __future__ import annotations

import logging
import time
import urllib.parse
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


class WikidataProvider(BaseProvider):
    """Fetch images from Wikidata entities via the P18 image property."""

    name = "wikidata"

    SUPPORTED_VISUAL_TYPES = {"photo"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.api_base = cfg.get(
            "wikidata_api_base", "https://www.wikidata.org"
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
        """Search Wikidata for images associated with entities matching *query*.

        Args:
            query: Search term (e.g. "Eiffel Tower").
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
        """3-step: search QID → fetch entity → extract P18 image."""
        # --- Step 1: search for entity QID ---
        search_params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "limit": min(limit, 50),
            "format": "json",
        }
        resp = self.session.get(
            f"{self.api_base}/w/api.php",
            params=search_params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        entities = data.get("search", [])
        if not entities:
            return []

        # --- Step 2 & 3: for each entity, get P18 and build Commons URL ---
        candidates: List[Candidate] = []
        for entity in entities[:limit]:
            qid = entity.get("id", "")
            label = entity.get("label", "")
            if not qid:
                continue

            image_filename = self._fetch_p18(qid)
            if not image_filename:
                continue

            image_url = self._commons_url(image_filename)
            if not image_url:
                continue

            candidates.append(Candidate(
                url=image_url,
                provider=self.name,
                visual_type="photo",
                width=0,
                height=0,
                license="CC0",
                attribution=f"Wikidata / {label} ({qid}) / CC0",
                title=label,
                score=0.65,
            ))

            if len(candidates) >= limit:
                break

        return candidates

    def _fetch_p18(self, qid: str) -> str | None:
        """Fetch the P18 (image) property value for a Wikidata entity.

        Returns the Commons filename (e.g. "Eiffel Tower, Paris.jpg") or None.
        """
        try:
            params = {
                "action": "wbgetentities",
                "ids": qid,
                "props": "claims",
                "format": "json",
            }
            resp = self.session.get(
                f"{self.api_base}/w/api.php",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.debug(f"[{self.name}] entity fetch failed for '{qid}': {exc}")
            return None

        entity_data = data.get("entities", {}).get(qid, {})
        p18_claims = entity_data.get("claims", {}).get("P18", [])

        if not p18_claims:
            return None

        # Take the first P18 value
        mainsnak = p18_claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", "")

        if isinstance(value, str) and value:
            return value

        return None

    @staticmethod
    def _commons_url(filename: str) -> str | None:
        """Convert a Commons filename to a direct image URL.

        Uses the Wikimedia Commons URL pattern:
          https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/{filename}

        Where {a} is the first char and {ab} are the first two chars of the
        MD5 hash of the filename (with spaces replaced by underscores).
        """
        if not filename:
            return None

        import hashlib

        # Commons uses underscores instead of spaces
        normalized = filename.replace(" ", "_")

        md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()
        a = md5[0]
        ab = md5[0:2]

        encoded = urllib.parse.quote(normalized)
        return (
            f"https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/{encoded}"
        )
