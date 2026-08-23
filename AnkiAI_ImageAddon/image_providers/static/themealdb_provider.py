"""TheMealDB image provider for AnkiAI ImageAddon.

Endpoint: https://www.themealdb.com/api/json/v1/1/search.php?s={query}
Extracts strMealThumb from meal results.

License: CC-BY
Rate limit: ~100 req/hr
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


class TheMealDBProvider(BaseProvider):
    """Fetch meal photos from TheMealDB free API."""

    name = "themealdb"

    SUPPORTED_VISUAL_TYPES = {"photo"}

    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
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
        """Search TheMealDB for meal photos matching *query*.

        Args:
            query: Search term (e.g. "chicken teriyaki").
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
        """Search TheMealDB and extract strMealThumb from each result."""
        resp = self.session.get(
            f"https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": query},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        meals = data.get("meals")
        if not meals:  # null or empty list when no results
            return []

        candidates: List[Candidate] = []
        for meal in meals[:limit]:
            thumb_url = meal.get("strMealThumb", "")
            if not thumb_url:
                continue

            meal_name = meal.get("strMeal", "")
            category = meal.get("strCategory", "")
            area = meal.get("strArea", "")

            # Build a descriptive attribution
            parts = []
            if meal_name:
                parts.append(meal_name)
            if category:
                parts.append(category)
            if area:
                parts.append(area)
            detail = " — ".join(parts) if parts else "TheMealDB"
            attribution = f"{detail} / TheMealDB / CC-BY"

            candidates.append(Candidate(
                url=thumb_url,
                provider=self.name,
                visual_type="photo",
                width=0,
                height=0,
                license="CC-BY",
                attribution=attribution,
                title=meal_name,
                score=0.5,
            ))

        return candidates
