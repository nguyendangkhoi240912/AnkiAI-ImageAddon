"""Noun Project icon provider for AnkiAI ImageAddon.

Uses the Noun Project v3 API with OAuth2 client_credentials auth.
Free tier: ~100 requests/day.  Icons are CC-BY-3.0; premium icons are filtered out.
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


class NewNounProjectProvider(BaseProvider):
    """Provider for the Noun Project icon API (v3, OAuth2).

    Config keys:
        noun_project_api_key: OAuth2 client_id (required)
        noun_project_api_secret: OAuth2 client_secret (required)
        provider_timeout_s: HTTP timeout in seconds (default: 10)
    """

    name = "noun_project"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.api_key = self.config.get("noun_project_api_key", "")
        self.api_secret = self.config.get("noun_project_api_secret", "")
        self.timeout = self.config.get("provider_timeout_s", 10)
        self._session = requests.Session()
        self._token: str = ""
        self._token_expires: float = 0.0

    # ------------------------------------------------------------------
    # OAuth2 token management
    # ------------------------------------------------------------------

    def _ensure_token(self) -> bool:
        """Obtain or refresh the OAuth2 access token.

        Returns True if a valid token is available, False otherwise.
        """
        if self._token and time.time() < self._token_expires:
            return True

        if not self.api_key or not self.api_secret:
            logger.debug("noun_project: missing API key/secret, skipping")
            return False

        try:
            resp = self._session.post(
                "https://api.thenounproject.com/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                },
                auth=(self.api_key, self.api_secret),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._token = token_data.get("access_token", "")
            expires_in = token_data.get("expires_in", 3600)
            # Refresh 60 seconds early to avoid edge-case expiry
            self._token_expires = time.time() + expires_in - 60
            return bool(self._token)
        except Exception as exc:
            logger.warning("noun_project OAuth2 token error: %s", exc)
            self._token = ""
            self._token_expires = 0.0
            return False

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    def search(self, query: str, visual_type: str = "icon", limit: int = 10) -> List[Candidate]:
        if visual_type != "icon":
            return []

        quota = _get_quota()
        if not quota.allow(self.name):
            logger.debug("noun_project: quota denied")
            return []

        if not self._ensure_token():
            _get_health().report(self.name, latency_s=0, ok=False)
            return []

        t0 = time.perf_counter()
        try:
            resp = self._session.get(
                f"https://api.thenounproject.com/v3/icons/search/{query}",
                headers={"Authorization": f"Bearer {self._token}"},
                params={"limit": limit},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            _get_health().report(self.name, latency_s=elapsed, ok=False)
            logger.warning("noun_project search error: %s", exc)
            return []

        elapsed = time.perf_counter() - t0
        _get_health().report(self.name, latency_s=elapsed, ok=True)
        quota.record(self.name)

        icons = data.get("icons", [])
        results: List[Candidate] = []
        for item in icons[:limit]:
            # Skip premium icons (free tier restriction)
            if item.get("is_premium", False):
                continue
            svg_url = item.get("svg_url") or item.get("icon_url", "")
            if not svg_url:
                continue
            results.append(Candidate(
                url=svg_url,
                provider=self.name,
                visual_type="icon",
                license="CC-BY-3.0",
                attribution=item.get("attribution", ""),
                title=item.get("term", "") or item.get("name", ""),
            ))

        return results
