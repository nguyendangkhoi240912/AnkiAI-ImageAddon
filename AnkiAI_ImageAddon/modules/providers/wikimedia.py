"""Wikimedia Commons and Servier Medical Art (SMART) providers."""

import logging
import time
from typing import Dict, List, Optional

from .base import ImageProviderError, WIKIMEDIA_HEADERS, _ImageProviderSessionManager, result_dict

logger = logging.getLogger(__name__)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


class _WikimediaBase:
    """Shared Wikimedia Action API helpers."""

    def __init__(self, name: str):
        self.base_url = COMMONS_API
        self.name = name
        self.session = _ImageProviderSessionManager.get_session(
            name, pool_connections=3, pool_maxsize=3
        )

    def _api_get(self, params: dict, timeout: int = 10) -> dict:
        params.setdefault("format", "json")
        params["origin"] = "*"
        response = self.session.get(
            self.base_url,
            params=params,
            headers=WIKIMEDIA_HEADERS,
            timeout=timeout,
        )
        if response.status_code != 200:
            raise ImageProviderError(f"{self.name} HTTP {response.status_code}")
        return response.json()

    def _search_titles(self, srsearch: str, per_page: int) -> List[str]:
        data = self._api_get(
            {
                "action": "query",
                "list": "search",
                "srsearch": srsearch,
                "srnamespace": "6",
                "srlimit": per_page,
            }
        )
        results = data.get("query", {}).get("search", [])
        if not results:
            raise ImageProviderError("No results")
        return [item["title"] for item in results[:per_page]]

    def _titles_to_image_urls(self, titles: List[str], keyword: str) -> List[Dict]:
        if not titles:
            return []
        data = self._api_get(
            {
                "action": "query",
                "titles": "|".join(titles),
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": 800,
            },
            timeout=12,
        )
        pages = data.get("query", {}).get("pages", {})
        images = []
        for page in pages.values():
            if page.get("missing"):
                continue
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            url = info.get("thumburl") or info.get("url")
            if not url:
                continue
            title = page.get("title", keyword)
            images.append(result_dict(url, title, self.name))
        if not images:
            raise ImageProviderError("No image URLs")
        return images

    def _search_with_retry(self, srsearch: str, per_page: int) -> List[Dict]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    time.sleep(0.2)
                titles = self._search_titles(srsearch, per_page)
                return self._titles_to_image_urls(titles, srsearch)
            except ImageProviderError:
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ImageProviderError(str(e))
                logger.debug(f"{self.name} retry {attempt + 1}: {e}")
        return []


class WikimediaCommonsProvider(_WikimediaBase):
    """Wikimedia Commons - general encyclopedic images."""

    def __init__(self):
        super().__init__("wikimedia")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        return self._search_with_retry(keyword, per_page)


class WikimediaSmartProvider(_WikimediaBase):
    """Servier Medical Art via Wikimedia Commons category filter."""

    SMART_CATEGORY = "Servier Medical Art"

    def __init__(self):
        super().__init__("wikimedia_smart")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        srsearch = f'{keyword} incategory:"{self.SMART_CATEGORY}"'
        return self._search_with_retry(srsearch, per_page)
