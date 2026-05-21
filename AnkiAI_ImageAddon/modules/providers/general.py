"""General-purpose image search providers (10 sources)."""

import hashlib
import hmac
import logging
import re
import time
import urllib.parse
from base64 import b64encode
from typing import Dict, List, Optional
from urllib.parse import quote, urlencode

from .base import ImageProviderError, _ImageProviderSessionManager, result_dict

logger = logging.getLogger(__name__)

# Providers that should use precise_term when available
PRECISE_TERM_GENERAL = set()


class PixabayProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ImageProviderError("Pixabay API key required")
        self.api_key = api_key
        self.name = "pixabay"
        self.session = _ImageProviderSessionManager.get_session("pixabay")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://pixabay.com/api/",
                params={
                    "key": self.api_key,
                    "q": keyword,
                    "image_type": "photo",
                    "per_page": per_page,
                    "safesearch": "true",
                },
                timeout=4,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Pixabay {response.status_code}")
            hits = response.json().get("hits", [])
            if not hits:
                raise ImageProviderError("No results")
            return [
                result_dict(
                    h.get("largeImageURL") or h.get("webformatURL"),
                    h.get("tags", keyword),
                    self.name,
                )
                for h in hits[:per_page]
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class FlickrProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ImageProviderError("Flickr API key required")
        self.api_key = api_key
        self.name = "flickr"
        self.session = _ImageProviderSessionManager.get_session("flickr")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://www.flickr.com/services/rest/",
                params={
                    "method": "flickr.photos.search",
                    "api_key": self.api_key,
                    "text": keyword,
                    "license": "4,5,6,9,10",
                    "content_type": 1,
                    "media": "photos",
                    "per_page": per_page,
                    "format": "json",
                    "nojsoncallback": 1,
                },
                timeout=5,
            )
            data = response.json()
            if data.get("stat") != "ok":
                raise ImageProviderError(data.get("message", "Flickr error"))
            photos = data.get("photos", {}).get("photo", [])
            if not photos:
                raise ImageProviderError("No results")
            images = []
            for p in photos[:per_page]:
                url = (
                    f"https://live.staticflickr.com/{p['server']}/"
                    f"{p['id']}_{p['secret']}_w.jpg"
                )
                images.append(result_dict(url, p.get("title", keyword), self.name))
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class GoogleCSEProvider:
    def __init__(self, api_key: str, cx: str):
        if not api_key or not cx:
            raise ImageProviderError("Google API key and CX required")
        self.api_key = api_key
        self.cx = cx
        self.name = "google_cse"
        self.session = _ImageProviderSessionManager.get_session("google_cse")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            response = self.session.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": self.api_key,
                    "cx": self.cx,
                    "q": keyword,
                    "searchType": "image",
                    "num": min(per_page, 10),
                },
                timeout=5,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Google CSE {response.status_code}")
            items = response.json().get("items", [])
            if not items:
                raise ImageProviderError("No results")
            return [
                result_dict(
                    item.get("link"),
                    item.get("title", keyword),
                    self.name,
                )
                for item in items[:per_page]
                if item.get("link")
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class DuckDuckGoImagesProvider:
    """Unofficial DuckDuckGo image search (no API key)."""

    def __init__(self):
        self.name = "duckduckgo"
        self.session = _ImageProviderSessionManager.get_session("duckduckgo")

    def _get_vqd(self, keyword: str) -> Optional[str]:
        response = self.session.get(
            "https://duckduckgo.com/",
            params={"q": keyword, "iax": "images", "ia": "images"},
            headers={"User-Agent": "AnkiAI-ImageAddon/5.0"},
            timeout=5,
        )
        match = re.search(r"vqd=([\d-]+)", response.text)
        return match.group(1) if match else None

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            vqd = self._get_vqd(keyword)
            if not vqd:
                raise ImageProviderError("Could not obtain DuckDuckGo token")
            response = self.session.get(
                "https://duckduckgo.com/i.js",
                params={
                    "l": "us-en",
                    "o": "json",
                    "q": keyword,
                    "vqd": vqd,
                    "f": ",,,",
                    "p": "1",
                },
                headers={"User-Agent": "AnkiAI-ImageAddon/5.0"},
                timeout=5,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"DuckDuckGo {response.status_code}")
            results = response.json().get("results", [])
            if not results:
                raise ImageProviderError("No results")
            return [
                result_dict(
                    r.get("image") or r.get("thumbnail"),
                    r.get("title", keyword),
                    self.name,
                )
                for r in results[:per_page]
                if r.get("image") or r.get("thumbnail")
            ]
        except Exception as e:
            raise ImageProviderError(str(e))


class YandexImagesProvider:
    """Yandex Images via HTML parse (unofficial, use with backoff)."""

    def __init__(self):
        self.name = "yandex"
        self.session = _ImageProviderSessionManager.get_session("yandex")
        self._last_request = 0.0

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            elapsed = time.time() - self._last_request
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
            self._last_request = time.time()

            response = self.session.get(
                "https://yandex.com/images/search",
                params={"text": keyword},
                headers={"User-Agent": "AnkiAI-ImageAddon/5.0"},
                timeout=8,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Yandex {response.status_code}")
            urls = re.findall(
                r'"url":"(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                response.text,
            )
            if not urls:
                urls = re.findall(r'data-bem=\'[^\']*"origUrl":"([^"]+)"', response.text)
            if not urls:
                raise ImageProviderError("No results")
            seen = set()
            images = []
            for url in urls:
                url = url.replace("\\/", "/")
                if url in seen:
                    continue
                seen.add(url)
                images.append(result_dict(url, keyword, self.name))
                if len(images) >= per_page:
                    break
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class NounProjectProvider:
    """The Noun Project - OAuth1 signed requests."""

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ImageProviderError("Noun Project key and secret required")
        self.api_key = api_key
        self.api_secret = api_secret
        self.name = "noun_project"
        self.session = _ImageProviderSessionManager.get_session("noun_project")

    def _oauth_header(self, method: str, url: str) -> str:
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": hashlib.md5(str(time.time()).encode()).hexdigest(),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_version": "1.0",
        }
        base_parts = [f"{k}={quote(str(v), safe='')}" for k, v in sorted(oauth_params.items())]
        base_string = "&".join(
            [
                method.upper(),
                quote(url, safe=""),
                quote("&".join(base_parts), safe=""),
            ]
        )
        signing_key = f"{quote(self.api_secret, safe='')}&"
        signature = b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        oauth_params["oauth_signature"] = signature
        header_parts = [
            f'{k}="{quote(str(v), safe="")}"' for k, v in sorted(oauth_params.items())
        ]
        return "OAuth " + ", ".join(header_parts)

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        try:
            url = "https://api.thenounproject.com/v2/icon"
            response = self.session.get(
                url,
                params={"query": keyword, "limit": per_page},
                headers={
                    "Authorization": self._oauth_header("GET", url),
                    "User-Agent": "AnkiAI-ImageAddon/5.0",
                },
                timeout=5,
            )
            if response.status_code != 200:
                raise ImageProviderError(f"Noun Project {response.status_code}")
            icons = response.json().get("icons", [])
            if not icons:
                raise ImageProviderError("No results")
            return [
                result_dict(
                    icon.get("thumbnail_url") or icon.get("preview_url"),
                    icon.get("term", keyword),
                    self.name,
                )
                for icon in icons[:per_page]
                if icon.get("thumbnail_url") or icon.get("preview_url")
            ]
        except Exception as e:
            raise ImageProviderError(str(e))
