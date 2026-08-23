"""
StorysetProvider — illustration search via Storyset API         [MS §17.2]
=========================================================================
Searches the Storyset API for free, customisable illustrations.
Returns SVG image URLs with CC-BY-4.0 licensing.

Endpoint: https://storyset.com/api/search/{query}

License: CC-BY-4.0
Rate:    100 req/hr
"""

from __future__ import annotations

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


def _get_health():
    from ..health import get_health_board
    return get_health_board()


def _get_quota():
    from ...modules.quota import get_quota_manager
    return get_quota_manager()


class StorysetProvider(BaseProvider):
    """Searches the Storyset API for customisable vector illustrations."""

    name = "storyset"

    SUPPORTED_VISUAL_TYPES = {"diagram_or_map", "metaphor_photo"}

    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._api_base = self._config.get(
            "storyset_api_base", "https://storyset.com/api"
        )
        self._timeout = self._config.get("provider_timeout_s", 10)
        self._session = requests.Session()
        self._session.timeout = self._timeout

    def search(
        self,
        query: str,
        visual_type: str = "diagram_or_map",
        limit: int = 10,
    ) -> List[Candidate]:
        """Search Storyset for illustrations matching the query.

        QuotaManager is checked before the API call (100 req/hr).

        Args:
            query:       Search query string.
            visual_type: Must be "diagram_or_map" or "metaphor_photo".
            limit:       Maximum number of candidates to return.

        Returns:
            List of Candidate objects, or empty list on error / quota exhausted.
        """
        t0 = time.perf_counter()
        ok = False
        try:
            if visual_type not in self.SUPPORTED_VISUAL_TYPES:
                return []

            # QuotaManager check
            quota = _get_quota()
            if not quota.allow("storyset"):
                logger.info("StorysetProvider: quota exhausted, skipping")
                return []

            url = f"{self._api_base}/search/{query}"
            resp = self._session.get(url, timeout=self._timeout)
            resp.raise_for_status()

            body = resp.json()
            illustrations = body.get("data", {}).get("illustrations", [])

            if not illustrations:
                logger.debug("StorysetProvider: no results for '%s'", query)
                ok = True  # successful call, just empty results
                return []

            # Record quota usage
            quota.record("storyset", tokens=0)

            candidates: List[Candidate] = []
            for item in illustrations[:limit]:
                image_url = item.get("image", "")
                title = item.get("title", "")

                if not image_url:
                    continue

                candidates.append(
                    Candidate(
                        url=image_url,
                        provider=self.name,
                        visual_type=visual_type,
                        width=0,
                        height=0,
                        license="CC-BY-4.0",
                        attribution="Storyset (https://storyset.com)",
                        title=title,
                        score=0.7,
                    )
                )

            ok = True
            return candidates

        except Exception:
            logger.exception("StorysetProvider: error searching for '%s'", query)
            return []

        finally:
            latency = time.perf_counter() - t0
            _get_health().report(self.name, latency, ok)
