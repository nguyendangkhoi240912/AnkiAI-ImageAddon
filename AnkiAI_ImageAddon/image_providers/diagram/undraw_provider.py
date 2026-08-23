"""
UnDrawProvider — illustration search via local index            [MS §17.2]
=========================================================================
Downloads the unDraw illustration index once, caches it locally in
user_files/undraw_index.json, and searches by title locally.
After the initial download, no further API calls are needed.

SVG URLs support color customization via the `color` query parameter:
    {image_url}&color={accent_color}

License: MIT (unDraw)
Rate:    Unlimited
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List

import requests

from ..base_provider import BaseProvider, Candidate

logger = logging.getLogger(__name__)

USER_FILES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_files"
)

_INDEX_PATH = os.path.join(USER_FILES, "undraw_index.json")


def _get_health():
    from ..health import get_health_board
    return get_health_board()


class UnDrawProvider(BaseProvider):
    """Searches a locally-cached unDraw illustration index by title."""

    name = "undraw"

    SUPPORTED_VISUAL_TYPES = {"icon", "diagram_or_map"}

    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._index_url = self._config.get(
            "undraw_index_url", "https://undraw.co/api/images"
        )
        self._accent_color = self._config.get("undraw_accent_color", "#2196F3")
        self._timeout = self._config.get("provider_timeout_s", 10)
        self._session = requests.Session()
        self._session.timeout = self._timeout
        self._index: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _ensure_index(self) -> bool:
        """Load the local index if available; otherwise download and cache it.

        Returns:
            True if the index is populated (from cache or fresh download),
            False on failure.
        """
        if self._index:
            return True

        # Try loading from local cache
        if os.path.isfile(_INDEX_PATH):
            try:
                with open(_INDEX_PATH, "r", encoding="utf-8") as fh:
                    self._index = json.load(fh)
                if self._index:
                    logger.debug(
                        "UnDrawProvider: loaded %d entries from cache", len(self._index)
                    )
                    return True
            except Exception:
                logger.warning("UnDrawProvider: failed to read cached index", exc_info=True)

        # Download from the API
        try:
            resp = self._session.get(self._index_url, timeout=self._timeout)
            resp.raise_for_status()
            body = resp.json()
            # API returns {"data": [{"title": "...", "image": "https://..."}, ...]}
            entries = body.get("data", [])
            if not entries:
                logger.warning("UnDrawProvider: API returned empty data")
                return False

            self._index = entries

            # Persist to disk for future sessions
            os.makedirs(USER_FILES, exist_ok=True)
            with open(_INDEX_PATH, "w", encoding="utf-8") as fh:
                json.dump(self._index, fh, ensure_ascii=False)

            logger.info(
                "UnDrawProvider: downloaded & cached %d entries", len(self._index)
            )
            return True

        except Exception:
            logger.exception("UnDrawProvider: failed to download index")
            return False

    @staticmethod
    def _match_score(query: str, title: str) -> float:
        """Simple relevance score: proportion of query words found in title."""
        if not title:
            return 0.0
        q_words = set(query.lower().split())
        t_words = set(title.lower().split())
        if not q_words:
            return 0.0
        overlap = q_words & t_words
        return len(overlap) / len(q_words)

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        visual_type: str = "diagram_or_map",
        limit: int = 10,
    ) -> List[Candidate]:
        """Search the local unDraw index by title.

        No API call after the first index download; QuotaManager check is
        unnecessary (unlimited rate).

        Args:
            query:       Search query — matched against illustration titles.
            visual_type: Must be "icon" or "diagram_or_map".
            limit:       Maximum number of candidates to return.

        Returns:
            List of Candidate objects with SVG URLs (color-customised),
            or empty list on error.
        """
        t0 = time.perf_counter()
        ok = False
        try:
            if visual_type not in self.SUPPORTED_VISUAL_TYPES:
                return []

            if not self._ensure_index():
                return []

            # Score every entry and sort by relevance
            scored: List[tuple] = []
            for entry in self._index:
                title = entry.get("title", "")
                score = self._match_score(query, title)
                if score > 0:
                    scored.append((score, entry))

            scored.sort(key=lambda pair: pair[0], reverse=True)
            top_entries = scored[:limit]

            accent = self._accent_color.lstrip("#")

            candidates: List[Candidate] = []
            for score, entry in top_entries:
                image_url = entry.get("image", "")
                title = entry.get("title", "")

                if not image_url:
                    continue

                # Append color customization if the URL supports query params
                # unDraw SVG URLs accept &color=<hex>
                separator = "&" if "?" in image_url else "?"
                colored_url = f"{image_url}{separator}color={accent}"

                candidates.append(
                    Candidate(
                        url=colored_url,
                        provider=self.name,
                        visual_type=visual_type,
                        width=0,
                        height=0,
                        license="MIT",
                        attribution="unDraw (https://undraw.co)",
                        title=title,
                        score=round(score, 3),
                    )
                )

            ok = True
            return candidates

        except Exception:
            logger.exception("UnDrawProvider: error searching for '%s'", query)
            return []

        finally:
            latency = time.perf_counter() - t0
            _get_health().report(self.name, latency, ok)
