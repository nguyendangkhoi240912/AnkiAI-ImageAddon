"""Noto Emoji SVG icon provider for AnkiAI ImageAddon.

Reuses the same emoji_index.json created by OpenMojiProvider (shared Unicode
codepoints).  SVGs are served by Google Fonts gstatic.  No API calls per
query — all searching is local.
License: Apache-2.0.  Rate: unlimited.
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


class NotoEmojiProvider(BaseProvider):
    """Provider for Google Noto Emoji icons via local index.

    Shares the emoji_index.json index with OpenMojiProvider.

    Config keys:
        noto_emoji_base_url: Base URL for Noto Emoji SVGs
            (default: https://fonts.gstatic.com/s/notoemoji/v1)
        provider_timeout_s: HTTP timeout for initial index download (default: 15)
    """

    name = "noto_emoji"

    _INDEX_FILE = os.path.join(USER_FILES, "emoji_index.json")

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_url = self.config.get(
            "noto_emoji_base_url",
            "https://fonts.gstatic.com/s/notoemoji/v1",
        )
        self.timeout = self.config.get("provider_timeout_s", 15)
        self._index: List[Dict] = []

    # ------------------------------------------------------------------
    # Index management (shared with OpenMoji)
    # ------------------------------------------------------------------

    def _load_index(self) -> List[Dict]:
        """Load the shared emoji index from disk."""
        if self._index:
            return self._index

        if os.path.isfile(self._INDEX_FILE):
            try:
                with open(self._INDEX_FILE, "r", encoding="utf-8") as fh:
                    self._index = json.load(fh)
                return self._index
            except Exception as exc:
                logger.warning("noto_emoji: failed to read local index: %s", exc)

        # The OpenMoji provider is the canonical downloader; if the file
        # doesn't exist yet, try downloading it ourselves from OpenMoji.
        fallback_url = (
            "https://raw.githubusercontent.com/hfg-gmuend/openmoji"
            "/master/data/openmoji.json"
        )
        try:
            os.makedirs(USER_FILES, exist_ok=True)
            session = requests.Session()
            resp = session.get(fallback_url, timeout=self.timeout)
            resp.raise_for_status()
            self._index = resp.json()
            with open(self._INDEX_FILE, "w", encoding="utf-8") as fh:
                json.dump(self._index, fh, ensure_ascii=False)
            logger.info("noto_emoji: downloaded index (%d entries)", len(self._index))
        except Exception as exc:
            logger.warning("noto_emoji: failed to download index: %s", exc)
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
            logger.warning("noto_emoji search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)

        results: List[Candidate] = []
        for entry in matches[:limit]:
            hexcode = entry.get("hexcode", "")
            if not hexcode:
                continue
            # Noto uses lowercase codepoint with hyphens preserved
            codepoint = hexcode.lower()
            svg_url = f"{self.base_url}/{codepoint}.svg"
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="Apache-2.0",
                attribution="Google Noto Emoji",
                title=entry.get("annotation", ""),
            ))

        return results
