"""Game-icons.net SVG icon provider for AnkiAI ImageAddon.

Downloads the game-icons.net JSON index once, then searches locally by name.
SVGs are fetched on demand from game-icons.net.  No API calls per query
after the initial download.
License: CC-BY-3.0.  Rate: unlimited.
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


class GameIconsProvider(BaseProvider):
    """Provider for game-icons.net SVG icons via local index.

    Config keys:
        gameicons_index_url: URL for the icons JSON index
            (default: https://game-icons.net/data/json/icons.json)
        provider_timeout_s: HTTP timeout in seconds (default: 15)
    """

    name = "gameicons"

    _INDEX_FILE = os.path.join(USER_FILES, "gameicons_index.json")

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.index_url = self.config.get(
            "gameicons_index_url",
            "https://game-icons.net/data/json/icons.json",
        )
        self.timeout = self.config.get("provider_timeout_s", 15)
        self._session = requests.Session()
        self._index: List[Dict] = []

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _load_index(self) -> List[Dict]:
        """Load the game-icons index from disk, downloading it first if needed."""
        if self._index:
            return self._index

        if os.path.isfile(self._INDEX_FILE):
            try:
                with open(self._INDEX_FILE, "r", encoding="utf-8") as fh:
                    self._index = json.load(fh)
                return self._index
            except Exception as exc:
                logger.warning("gameicons: failed to read local index: %s", exc)

        # Download and cache
        try:
            os.makedirs(USER_FILES, exist_ok=True)
            resp = self._session.get(self.index_url, timeout=self.timeout)
            resp.raise_for_status()
            self._index = resp.json()
            with open(self._INDEX_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._index, fh, ensure_ascii=False)
            logger.info("gameicons: downloaded index (%d icons)", len(self._index))
        except Exception as exc:
            logger.warning("gameicons: failed to download index: %s", exc)
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
                icon_name = (entry.get("name") or "").lower()
                if q_lower in icon_name:
                    matches.append(entry)
                if len(matches) >= limit * 2:
                    break
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=False)
            logger.warning("gameicons search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)

        results: List[Candidate] = []
        for entry in matches[:limit]:
            path = entry.get("path", "")
            if not path:
                continue
            svg_url = f"https://game-icons.net/icons/{path}.svg"
            author = entry.get("author", "")
            attribution = f"game-icons.net – {author}" if author else "game-icons.net"
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="CC-BY-3.0",
                attribution=attribution,
                title=entry.get("name", ""),
            ))

        return results
