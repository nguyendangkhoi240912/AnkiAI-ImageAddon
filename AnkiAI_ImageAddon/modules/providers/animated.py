"""Animated image providers: GIFs, stickers, and icon-like motion assets."""

import logging
from typing import Dict, List, Optional

from .base import ImageProviderError, _ImageProviderSessionManager, result_dict

logger = logging.getLogger(__name__)


class KLIPYProvider:
    """KLIPY GIF search API."""

    def __init__(self, app_key: str):
        if not app_key:
            raise ImageProviderError("KLIPY app key required")
        self.app_key = app_key
        self.name = "klipy"
        self.session = _ImageProviderSessionManager.get_session("klipy")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                f"https://api.klipy.ai/api/v1/{self.app_key}/gifs/search",
                params={
                    "q": keyword,
                    "page": 1,
                    "per_page": min(max(per_page, 8), 50),
                },
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"KLIPY {response.status_code}")
            payload = response.json()
            items = (
                payload.get("data", {}).get("data", [])
                if isinstance(payload, dict)
                else []
            )
            if not items:
                raise ImageProviderError("No results")
            images: List[Dict] = []
            for item in items[:per_page]:
                file_obj = item.get("file", {})
                for size_key in ("md", "sm", "hd"):
                    variant = file_obj.get(size_key, {})
                    url = variant.get("gif", {}).get("url") or variant.get("mp4", {}).get("url")
                    if url:
                        images.append(
                            result_dict(
                                url,
                                item.get("title") or item.get("slug") or keyword,
                                self.name,
                            )
                        )
                        break
            if not images:
                raise ImageProviderError("No KLIPY image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class GIPHYProvider:
    """GIPHY GIF search API."""

    def __init__(self, api_key: str, client_key: str = "ankiai-image-addon"):
        if not api_key:
            raise ImageProviderError("GIPHY API key required")
        self.api_key = api_key
        self.client_key = client_key
        self.name = "giphy"
        self.session = _ImageProviderSessionManager.get_session("giphy")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://api.giphy.com/v1/gifs/search",
                params={
                    "api_key": self.api_key,
                    "q": keyword,
                    "client_key": self.client_key,
                    "limit": min(max(per_page, 1), 50),
                    "rating": "g",
                    "lang": "en",
                },
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"GIPHY {response.status_code}")
            payload = response.json()
            data = payload.get("data", [])
            if not data:
                raise ImageProviderError("No results")
            images: List[Dict] = []
            for item in data[:per_page]:
                images.append(
                    result_dict(
                        item.get("images", {}).get("original", {}).get("url"),
                        item.get("title") or keyword,
                        self.name,
                    )
                )
            images = [img for img in images if img.get("url")]
            if not images:
                raise ImageProviderError("No GIPHY image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class TenorProvider:
    """Tenor GIF search API."""

    def __init__(self, api_key: str, client_key: str = "ankiai-image-addon"):
        if not api_key:
            raise ImageProviderError("Tenor API key required")
        self.api_key = api_key
        self.client_key = client_key
        self.name = "tenor"
        self.session = _ImageProviderSessionManager.get_session("tenor")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://tenor.googleapis.com/v2/search",
                params={
                    "key": self.api_key,
                    "client_key": self.client_key,
                    "q": keyword,
                    "limit": min(max(per_page, 1), 50),
                    "contentfilter": "low",
                    "media_filter": "gif",
                    "locale": "en_US",
                    "country": "US",
                },
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Tenor {response.status_code}")
            payload = response.json()
            results = payload.get("results", [])
            if not results:
                raise ImageProviderError("No results")
            images: List[Dict] = []
            for item in results[:per_page]:
                media = item.get("media_formats", {})
                url = (
                    media.get("gif", {}).get("url")
                    or media.get("tinygif", {}).get("url")
                    or media.get("nanogif", {}).get("url")
                )
                if url:
                    images.append(
                        result_dict(
                            url,
                            item.get("content_description") or keyword,
                            self.name,
                        )
                    )
            if not images:
                raise ImageProviderError("No Tenor image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class PixabayAnimatedProvider:
    """Pixabay search with GIF-friendly image_type."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ImageProviderError("Pixabay API key required")
        self.api_key = api_key
        self.name = "pixabay_animated"
        self.session = _ImageProviderSessionManager.get_session("pixabay_animated")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://pixabay.com/api/",
                params={
                    "key": self.api_key,
                    "q": keyword,
                    "image_type": "all",
                    "per_page": per_page,
                    "safesearch": "true",
                },
                timeout=6,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Pixabay {response.status_code}")
            hits = response.json().get("hits", [])
            if not hits:
                raise ImageProviderError("No results")
            images: List[Dict] = []
            for hit in hits[:per_page]:
                url = hit.get("webformatURL") or hit.get("largeImageURL")
                if url:
                    images.append(result_dict(url, hit.get("tags", keyword), self.name))
            if not images:
                raise ImageProviderError("No Pixabay image URLs")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class IconScoutProvider:
    """Best-effort IconScout provider via public item/collection search endpoints.

    IconScout's public API surface is heavily permissioned; this provider is
    intentionally defensive and falls back cleanly when the endpoint shape
    differs or access is restricted.
    """

    def __init__(self, access_token: str = ""):
        self.access_token = access_token
        self.name = "iconscout"
        self.session = _ImageProviderSessionManager.get_session("iconscout")

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "AnkiAI-ImageAddon/5.0"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        endpoints = [
            ("https://iconscout.com/api/v2/search", {"query": keyword, "limit": per_page}),
            ("https://iconscout.com/api/v2/items/search", {"query": keyword, "limit": per_page}),
            ("https://iconscout.com/api/v2/items", {"query": keyword, "limit": per_page}),
        ]
        last_error = None
        for url, params in endpoints:
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=self._headers(),
                    timeout=8,
                )
                if response.status_code != 200:
                    last_error = f"IconScout {response.status_code}"
                    continue
                payload = response.json()
                items = (
                    payload.get("response", {}).get("data")
                    or payload.get("data")
                    or payload.get("items")
                    or []
                )
                images: List[Dict] = []
                for item in items[:per_page]:
                    file_url = None
                    if isinstance(item, dict):
                        file_url = (
                            item.get("download_url")
                            or item.get("url")
                            or item.get("preview_url")
                        )
                        if not file_url:
                            media = item.get("media", {})
                            if isinstance(media, dict):
                                file_url = (
                                    media.get("gif")
                                    or media.get("mp4")
                                    or media.get("webp")
                                    or media.get("lottie")
                                )
                        if isinstance(file_url, dict):
                            file_url = file_url.get("url")
                    if file_url:
                        title = (
                            item.get("name")
                            or item.get("title")
                            or item.get("slug")
                            or keyword
                        )
                        images.append(result_dict(file_url, title, self.name))
                if images:
                    return images
                last_error = "No results"
            except Exception as e:
                last_error = str(e)
                continue
        raise ImageProviderError(last_error or "IconScout unavailable")
