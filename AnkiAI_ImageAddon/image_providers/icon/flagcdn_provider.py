"""FlagCDN SVG flag provider for AnkiAI ImageAddon.

Downloads the flagcdn.com index once, then searches locally by country name.
SVGs are served directly from flagcdn.com.  No API calls per query after the
initial download.
License: Public Domain.  Rate: unlimited.
"""

import json
import logging
import os
import time
from typing import Dict, List, Any

import requests

from ..base_provider import BaseProvider, Candidate

logger = logging.getLogger(__name__)

USER_FILES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_files")


def _get_health():
    from ..health import get_health_board
    return get_health_board()


class FlagCDNProvider(BaseProvider):
    """Provider for country flag SVGs from flagcdn.com via local index.

    Config keys:
        flagcdn_index_url: URL for the flags JSON index
            (default: https://flagcdn.com/flags.json)
        provider_timeout_s: HTTP timeout in seconds (default: 15)
    """

    name = "flagcdn"

    _INDEX_FILE = os.path.join(USER_FILES, "flags_index.json")

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.index_url = self.config.get(
            "flagcdn_index_url",
            "https://flagcdn.com/flags.json",
        )
        self.timeout = self.config.get("provider_timeout_s", 15)
        self._session = requests.Session()
        self._index: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _load_index(self) -> Dict[str, Dict]:
        """Load the flags index from disk, downloading it first if needed."""
        if self._index:
            return self._index

        if os.path.isfile(self._INDEX_FILE):
            try:
                with open(self._INDEX_FILE, "r", encoding="utf-8") as fh:
                    self._index = json.load(fh)
                return self._index
            except Exception as exc:
                logger.warning("flagcdn: failed to read local index: %s", exc)

        # Download and cache
        try:
            os.makedirs(USER_FILES, exist_ok=True)
            resp = self._session.get(self.index_url, timeout=self.timeout)
            resp.raise_for_status()
            self._index = resp.json()
            with open(self._INDEX_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._index, fh, ensure_ascii=False)
            logger.info("flagcdn: downloaded index (%d countries)", len(self._index))
        except Exception as exc:
            logger.warning("flagcdn: failed to download index: %s", exc)
            self._index = {}

        return self._index

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    def search(self, query: str, visual_type: str = "icon", limit: int = 10) -> List[Candidate]:
        if visual_type != "icon":
            return []

        t0 = time.perf_counter()
        try:
            index = self._load_index()
            q_lower = query.lower()

            matches: List[tuple] = []  # (code, name)
            for code, info in index.items():
                name = (info.get("name") or "").lower()
                if q_lower in name:
                    matches.append((code, info.get("name", "")))
                if len(matches) >= limit:
                    break
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=False)
            logger.warning("flagcdn search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)

        results: List[Candidate] = []
        for code, name in matches[:limit]:
            svg_url = f"https://flagcdn.com/{code}.svg"
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="Public Domain",
                attribution="flagcdn.com",
                title=name,
            ))

        return results
