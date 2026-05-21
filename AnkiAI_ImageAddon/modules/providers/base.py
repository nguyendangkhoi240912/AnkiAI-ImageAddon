"""Shared utilities for image providers."""

import logging
import threading
import time
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

WIKIMEDIA_HEADERS = {
    "User-Agent": "AnkiAI-ImageAddon/5.0 (Educational flashcard tool; contact: addon-user)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://commons.wikimedia.org/",
}


class ImageProviderError(Exception):
    """Exception for image provider errors."""
    pass


class _ImageProviderSessionManager:
    """Manage HTTP sessions with global connection pooling."""

    _sessions: Dict = {}
    _lock = threading.Lock()

    @classmethod
    def get_session(
        cls, name: str = "default", pool_connections: int = 5, pool_maxsize: int = 5
    ) -> requests.Session:
        session_key = f"{name}_{pool_connections}_{pool_maxsize}"
        with cls._lock:
            if session_key not in cls._sessions:
                session = requests.Session()
                adapter = HTTPAdapter(
                    pool_connections=pool_connections,
                    pool_maxsize=pool_maxsize,
                    max_retries=Retry(total=1, backoff_factor=0.05),
                )
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                cls._sessions[session_key] = session
            return cls._sessions[session_key]

    @classmethod
    def close_all(cls):
        with cls._lock:
            for session in cls._sessions.values():
                try:
                    session.close()
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")
            cls._sessions.clear()


def result_dict(url: str, title: str, provider: str) -> Dict:
    return {"url": url, "title": title, "provider": provider}


def filter_valid_results(items: List[Dict]) -> List[Dict]:
    return [i for i in items if i.get("url")]
