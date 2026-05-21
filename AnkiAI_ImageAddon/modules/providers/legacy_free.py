"""Legacy free providers kept from v4.x."""

import logging
from typing import Dict, List

from .base import ImageProviderError, _ImageProviderSessionManager, result_dict

logger = logging.getLogger(__name__)


class PexelsProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ImageProviderError("Pexels API key required")
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/v1"
        self.name = "pexels"
        self.session = _ImageProviderSessionManager.get_session("pexels")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                f"{self.base_url}/search",
                headers={"Authorization": self.api_key},
                params={"query": keyword, "per_page": per_page, "page": 1},
                timeout=4,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Pexels {response.status_code}")
            results = response.json().get("photos", [])
            if not results:
                raise ImageProviderError("No results")
            return [
                result_dict(p["src"]["large"], p.get("alt", keyword), self.name)
                for p in results[:per_page]
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class UnsplashProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ImageProviderError("Unsplash API key required")
        self.api_key = api_key
        self.name = "unsplash"
        self.session = _ImageProviderSessionManager.get_session("unsplash")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {self.api_key}"},
                params={
                    "query": keyword,
                    "per_page": per_page,
                    "orientation": "landscape",
                },
                timeout=4,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Unsplash {response.status_code}")
            results = response.json().get("results", [])
            if not results:
                raise ImageProviderError("No results")
            return [
                result_dict(p["urls"]["regular"], p.get("description", keyword), self.name)
                for p in results[:per_page]
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class OpenverseProvider:
    def __init__(self, api_token: str = ""):
        self.api_token = api_token
        self.base_url = "https://api.openverse.engineering/v1"
        self.name = "openverse"
        self.session = _ImageProviderSessionManager.get_session("openverse")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            headers = {"User-Agent": "AnkiAI-ImageAddon/5.0"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            response = self.session.get(
                f"{self.base_url}/images",
                params={
                    "q": keyword,
                    "page_size": per_page,
                    "license": "cc0,pdm,by,by-sa",
                },
                headers=headers,
                timeout=5,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Openverse {response.status_code}")
            results = response.json().get("results", [])
            if not results:
                raise ImageProviderError("No results")
            return [
                result_dict(
                    img.get("url") or img.get("thumbnail"),
                    img.get("title", keyword),
                    self.name,
                )
                for img in results[:per_page]
                if img.get("url") or img.get("thumbnail")
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class LoremPicsumProvider:
    def __init__(self):
        self.name = "lorem_picsum"

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        return [
            result_dict(
                f"https://picsum.photos/seed/{hash(keyword) % 10000 + i}/600/400",
                f"{keyword} (stock {i + 1})",
                self.name,
            )
            for i in range(per_page)
        ]


class LibraryOfCongressProvider:
    def __init__(self):
        self.name = "loc"
        self.session = _ImageProviderSessionManager.get_session("loc")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            response = self.session.get(
                "https://www.loc.gov/search",
                params={"q": keyword, "fo": "json", "fa": "online-format:image"},
                timeout=5,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"LOC {response.status_code}")
            results = response.json().get("results", [])
            return [
                result_dict(item["image_url"], item.get("title", keyword), self.name)
                for item in results[:per_page]
                if item.get("image_url")
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class MetMuseumProvider:
    def __init__(self):
        self.base_url = "https://collectionapi.metmuseum.org/public/collection/v1"
        self.name = "metmuseum"
        self.session = _ImageProviderSessionManager.get_session("metmuseum")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            response = self.session.get(
                f"{self.base_url}/search",
                params={"q": keyword, "hasImages": "true"},
                timeout=5,
            )
            obj_ids = response.json().get("objectIDs") or []
            if not obj_ids:
                raise ImageProviderError("No results")
            images = []
            for obj_id in obj_ids[:per_page]:
                try:
                    obj = self.session.get(
                        f"{self.base_url}/objects/{obj_id}", timeout=3
                    ).json()
                    if obj.get("primaryImage"):
                        images.append(
                            result_dict(
                                obj["primaryImage"], obj.get("title", keyword), self.name
                            )
                        )
                except Exception:
                    continue
            if not images:
                raise ImageProviderError("No valid Met images")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class EuropeanaProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ImageProviderError("Europeana API key required")
        self.api_key = api_key
        self.name = "europeana"
        self.session = _ImageProviderSessionManager.get_session("europeana")

    def search(self, keyword: str, per_page: int = 2) -> List[Dict]:
        try:
            response = self.session.get(
                "https://api.europeana.eu/record/v2/search.json",
                params={
                    "query": keyword,
                    "wskey": self.api_key,
                    "rows": per_page,
                    "media": "true",
                },
                timeout=5,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Europeana {response.status_code}")
            results = response.json().get("items", [])
            return [
                result_dict(
                    item.get("edmPreview", [None])[0],
                    (item.get("title") or [keyword])[0],
                    self.name,
                )
                for item in results[:per_page]
                if item.get("edmPreview")
            ]
        except Exception as e:
            raise ImageProviderError(str(e))
