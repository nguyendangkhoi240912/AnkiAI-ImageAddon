"""Openclipart SVG icon provider for AnkiAI ImageAddon.

Searches the Openclipart JSON API for public-domain clipart.
License: CC0.  Rate: unlimited.
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


class OpenclipartProvider(BaseProvider):
    """Provider for Openclipart SVG search API.

    Config keys:
        openclipart_base: Base URL for the Openclipart API
            (default: https://openclipart.org/search/json)
        provider_timeout_s: HTTP timeout in seconds (default: 10)
    """

    name = "openclipart"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base = self.config.get("openclipart_base", "https://openclipart.org/search/json")
        self.timeout = self.config.get("provider_timeout_s", 10)
        self._session = requests.Session()

    def search(self, query: str, visual_type: str = "icon", limit: int = 10) -> List[Candidate]:
        if visual_type != "icon":
            return []

        quota = _get_quota()
        if not quota.allow(self.name):
            logger.debug("openclipart: quota denied")
            return []

        t0 = time.perf_counter()
        try:
            resp = self._session.get(
                self.base,
                params={"query": query, "limit": limit},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=False)
            logger.warning("openclipart search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)
        quota.record(self.name)

        results_list = data.get("results", []) if isinstance(data, dict) else data
        results: List[Candidate] = []
        for item in results_list[:limit]:
            svg_url = item.get("svg", "") or item.get("svg_url", "")
            if not svg_url:
                continue
            title = item.get("title", "") or item.get("name", "")
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="CC0",
                attribution="Openclipart",
                title=title,
            ))

        return results
