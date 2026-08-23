"""OpenMoji SVG icon provider for AnkiAI ImageAddon.

Downloads the OpenMoji JSON index once, then searches locally — zero API
calls per query after the initial download.  SVGs are fetched on demand.
License: CC-BY-SA-4.0.  Rate: unlimited (static files).
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


class OpenMojiProvider(BaseProvider):
    """Provider for OpenMoji icons via local index.

    Config keys:
        openmoji_index_url: URL for the OpenMoji JSON index
            (default: https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.json)
        provider_timeout_s: HTTP timeout in seconds (default: 15)
    """

    name = "openmoji"

    _INDEX_FILE = os.path.join(USER_FILES, "emoji_index.json")

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.index_url = self.config.get(
            "openmoji_index_url",
            "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.json",
        )
        self.timeout = self.config.get("provider_timeout_s", 15)
        self._session = requests.Session()
        self._index: List[Dict] = []

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _load_index(self) -> List[Dict]:
        """Load the emoji index from disk, downloading it first if needed."""
        if self._index:
            return self._index

        if os.path.isfile(self._INDEX_FILE):
            try:
                with open(self._INDEX_FILE, "r", encoding="utf-8") as fh:
                    self._index = json.load(fh)
                return self._index
            except Exception as exc:
                logger.warning("openmoji: failed to read local index: %s", exc)

        # Download and cache
        try:
            os.makedirs(USER_FILES, exist_ok=True)
            resp = self._session.get(self.index_url, timeout=self.timeout)
            resp.raise_for_status()
            self._index = resp.json()
            with open(self._INDEX_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._index, fh, ensure_ascii=False)
            logger.info("openmoji: downloaded index (%d entries)", len(self._index))
        except Exception as exc:
            logger.warning("openmoji: failed to download index: %s", exc)
            self._index = []

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

            matches: List[Dict] = []
            for entry in index:
                annotation = (entry.get("annotation") or "").lower()
                tags = [t.lower() for t in (entry.get("tags") or [])]
                if q_lower in annotation or any(q_lower in t for t in tags):
                    matches.append(entry)
                if len(matches) >= limit * 3:
                    break
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=False)
            logger.warning("openmoji search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)

        results: List[Candidate] = []
        for entry in matches[:limit]:
            hexcode = entry.get("hexcode", "")
            if not hexcode:
                continue
            svg_url = (
                f"https://raw.githubusercontent.com/hfg-gmuend/openmoji"
                f"/master/svg/{hexcode}.svg"
            )
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="CC-BY-SA-4.0",
                attribution="OpenMoji.org",
                title=entry.get("annotation", ""),
            ))

        return results
