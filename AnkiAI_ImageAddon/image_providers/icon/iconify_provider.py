"""Iconify SVG icon provider for AnkiAI ImageAddon.

Searches the Iconify API for open-source icon sets (MDI, FontAwesome, etc.).
Licences vary per icon set (MIT, Apache-2.0, etc.).
Rate limit: ~1000 requests/hour.
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


class IconifyProvider(BaseProvider):
    """Provider for Iconify icon search API.

    Config keys:
        iconify_base: Base URL for the Iconify API (default: https://api.iconify.design)
        provider_timeout_s: HTTP timeout in seconds (default: 10)
    """

    name = "iconify"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base = self.config.get("iconify_base", "https://api.iconify.design")
        self.timeout = self.config.get("provider_timeout_s", 10)
        self._session = requests.Session()

    def search(self, query: str, visual_type: str = "icon", limit: int = 10) -> List[Candidate]:
        if visual_type != "icon":
            return []

        quota = _get_quota()
        if not quota.allow(self.name):
            logger.debug("iconify: quota denied")
            return []

        t0 = time.perf_counter()
        try:
            url = f"{self.base}/search"
            resp = self._session.get(
                url,
                params={"query": query, "limit": limit},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=False)
            logger.warning("iconify search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)
        quota.record(self.name)

        icons = data.get("icons", [])
        results: List[Candidate] = []
        for entry in icons[:limit]:
            prefix = entry.get("prefix", "")
            icon_name = entry.get("name", "")
            if not prefix or not icon_name:
                continue
            svg_url = f"{self.base}/{prefix}/{icon_name}.svg"
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="MIT/Apache",
                attribution=f"Iconify/{prefix}",
                title=f"{prefix}:{icon_name}",
            ))

        return results
