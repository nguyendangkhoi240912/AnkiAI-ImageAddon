"""
Image Providers v5.0 - 20+ sources, domain routing, adaptive delay.
"""

import logging
import multiprocessing
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from .providers.base import ImageProviderError, _ImageProviderSessionManager
from .providers.scientific import SCIENTIFIC_PRECISE_PROVIDERS

# Re-export provider classes for backward compatibility
from .providers import (  # noqa: F401
    PexelsProvider,
    UnsplashProvider,
    OpenverseProvider,
    LoremPicsumProvider,
    LibraryOfCongressProvider,
    MetMuseumProvider,
    EuropeanaProvider,
    WikimediaCommonsProvider,
    WikimediaSmartProvider,
    PixabayProvider,
    FlickrProvider,
    GoogleCSEProvider,
    DuckDuckGoImagesProvider,
    YandexImagesProvider,
    NounProjectProvider,
    PubChemProvider,
    ChEMBLProvider,
    RCSBProvider,
    PhyloPicProvider,
    ISICProvider,
    EuropePMCProvider,
    NASAImagesProvider,
    CodeCogsProvider,
    BioiconsProvider,
)

logger = logging.getLogger(__name__)


class AdaptiveDelayManager:
    def __init__(self, base_delay_ms: int = 100, max_delay_ms: int = 2000):
        self.base_delay = base_delay_ms / 1000.0
        self.max_delay = max_delay_ms / 1000.0
        self.provider_delays: Dict[str, float] = {}
        self.last_failure_time: Dict[str, float] = {}
        self.lock = threading.Lock()

    def get_delay(self, provider_name: str) -> float:
        with self.lock:
            return self.provider_delays.get(provider_name, self.base_delay)

    def increase_delay(self, provider_name: str, increase_ms: int):
        with self.lock:
            current = self.provider_delays.get(provider_name, self.base_delay)
            new_delay = min(current + increase_ms / 1000.0, self.max_delay)
            self.provider_delays[provider_name] = new_delay
            self.last_failure_time[provider_name] = time.time()

    def reset_delay_if_expired(self, provider_name: str, reset_hours: int = 1):
        with self.lock:
            if provider_name in self.last_failure_time:
                elapsed = time.time() - self.last_failure_time[provider_name]
                if elapsed > reset_hours * 3600:
                    self.provider_delays[provider_name] = self.base_delay
                    del self.last_failure_time[provider_name]

    def apply_delay(self, provider_name: str):
        delay = self.get_delay(provider_name)
        if delay > 0:
            time.sleep(delay)


class RateLimitHandler:
    def __init__(self, pause_duration: int = 60):
        self.last_rate_limit: Dict[str, datetime] = {}
        self.pause_duration = pause_duration
        self.lock = threading.Lock()

    def is_rate_limited(self, provider_name: str) -> bool:
        with self.lock:
            if provider_name not in self.last_rate_limit:
                return False
            elapsed = datetime.now() - self.last_rate_limit[provider_name]
            if elapsed.total_seconds() < self.pause_duration:
                return True
            del self.last_rate_limit[provider_name]
            return False

    def handle_rate_limit(self, provider_name: str):
        with self.lock:
            self.last_rate_limit[provider_name] = datetime.now()
            logger.warning(f"{provider_name} rate limited - pause {self.pause_duration}s")

    def wait_if_limited(self, provider_name: str) -> bool:
        return self.is_rate_limited(provider_name)


class ImageScore:
    PROVIDER_SCORES = {
        "pexels": 95,
        "unsplash": 90,
        "pixabay": 85,
        "google_cse": 84,
        "flickr": 82,
        "duckduckgo": 78,
        "openverse": 75,
        "noun_project": 72,
        "wikimedia": 70,
        "wikimedia_smart": 88,
        "pubchem": 92,
        "chembl": 88,
        "rcsb": 86,
        "phylopic": 80,
        "nasa": 78,
        "isic": 85,
        "europe_pmc": 75,
        "bioicons": 82,
        "codecogs": 90,
        "yandex": 65,
        "loc": 60,
        "metmuseum": 62,
        "lorem_picsum": 50,
        "europeana": 68,
    }

    def __init__(self, url: str, provider: str, title: str = ""):
        self.url = url
        self.provider = provider
        self.title = title
        self.score = 0
        self.details: Dict = {}

    def calculate_score(self):
        self.score = self.PROVIDER_SCORES.get(self.provider, 50)
        self.details["provider_base"] = self.score
        if self.url:
            penalty = min(len(self.url) / 500, 20)
            self.score -= penalty
            self.details["url_quality"] = -penalty
        if self.title:
            bonus = min(len(self.title) / 5, 10)
            self.score += bonus
            self.details["title_relevance"] = bonus
        self.score = max(0, min(100, self.score))
        return self.score


class ImageCache:
    def __init__(self, ttl_minutes: int = 120):
        self.cache: Dict[str, Dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[List[str]]:
        with self.lock:
            if key not in self.cache:
                return None
            entry = self.cache[key]
            if datetime.now() > entry["expires"]:
                del self.cache[key]
                return None
            return entry["urls"]

    def set(self, key: str, urls: List[str]):
        with self.lock:
            self.cache[key] = {
                "urls": urls,
                "expires": datetime.now() + self.ttl,
            }


class ProviderStats:
    def __init__(self, provider_name: str):
        self.name = provider_name
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.avg_response_time = 0.0
        self.lock = threading.Lock()

    def record_success(self, response_time: float):
        with self.lock:
            self.total_requests += 1
            self.successful_requests += 1
            alpha = 0.2
            self.avg_response_time = (alpha * response_time) + (
                (1 - alpha) * self.avg_response_time
            )

    def record_failure(self):
        with self.lock:
            self.total_requests += 1
            self.failed_requests += 1

    def get_overall_score(self) -> float:
        with self.lock:
            if self.total_requests == 0:
                return 1.0
            reliability = max(
                0.0, self.successful_requests / self.total_requests
            )
            speed = (
                1.0
                if self.avg_response_time == 0
                else max(0.0, 1.0 / (1.0 + self.avg_response_time))
            )
            return (reliability * 0.7) + (speed * 0.3)


class SmartImageSelector:
    MAX_PROVIDERS_PER_SEARCH = 12

    def __init__(
        self,
        max_workers: int = 10,
        enable_adaptive_delay: bool = True,
        base_delay_ms: int = 100,
        max_delay_ms: int = 2000,
    ):
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = min(max_workers, cpu_count, 12)
        self.cache = ImageCache(ttl_minutes=120)
        self.providers: List[Tuple[str, object]] = []
        self.provider_domains: Dict[str, Set[str]] = {}
        self.provider_stats: Dict[str, ProviderStats] = {}
        self.rate_limiter = RateLimitHandler()
        self.delay_manager = (
            AdaptiveDelayManager(base_delay_ms, max_delay_ms)
            if enable_adaptive_delay
            else None
        )
        self.lock = threading.Lock()

    def add_provider(
        self, name: str, provider: object, domains: Optional[Set[str]] = None
    ):
        with self.lock:
            self.providers.append((name, provider))
            self.provider_domains[name] = domains or {"general"}
            self.provider_stats[name] = ProviderStats(name)

    def _get_providers_sorted_by_performance(
        self, allowed_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, object]]:
        with self.lock:
            filtered = self.providers
            if allowed_ids is not None:
                filtered = [(n, p) for n, p in self.providers if n in allowed_ids]
            return sorted(
                filtered,
                key=lambda p: self.provider_stats[p[0]].get_overall_score(),
                reverse=True,
            )

    def _get_provider_timeout(self, provider_name: str) -> float:
        fast = {
            "pexels",
            "unsplash",
            "lorem_picsum",
            "pixabay",
            "duckduckgo",
            "codecogs",
        }
        medium = {
            "openverse",
            "google_cse",
            "flickr",
            "noun_project",
            "yandex",
            "nasa",
            "pubchem",
            "phylopic",
        }
        if provider_name in fast:
            return 2.0
        if provider_name in medium:
            return 3.5
        return 4.5

    def _search_term(
        self, name: str, keyword: str, precise_term: Optional[str]
    ) -> str:
        if (
            precise_term
            and precise_term.strip()
            and name in SCIENTIFIC_PRECISE_PROVIDERS
        ):
            return precise_term.strip()
        return keyword

    def _search_provider(
        self,
        provider: Tuple[str, object],
        keyword: str,
        precise_term: Optional[str] = None,
    ) -> List[ImageScore]:
        name, provider_obj = provider
        start_time = time.time()
        if self.delay_manager:
            self.delay_manager.apply_delay(name)
        try:
            if self.rate_limiter.wait_if_limited(name):
                return []
            search_kw = self._search_term(name, keyword, precise_term)
            results = provider_obj.search(search_kw, per_page=2)
            response_time = time.time() - start_time
            self.provider_stats[name].record_success(response_time)
            if self.delay_manager:
                self.delay_manager.reset_delay_if_expired(name)
            scored = []
            for img in results:
                if not img.get("url"):
                    continue
                score_obj = ImageScore(
                    img["url"],
                    provider_obj.name,
                    img.get("title", ""),
                )
                score_obj.calculate_score()
                scored.append(score_obj)
            return scored
        except Exception as e:
            self.provider_stats[name].record_failure()
            if self.delay_manager:
                if "429" in str(e) or "503" in str(e):
                    self.delay_manager.increase_delay(name, 500)
                elif "timeout" in str(e).lower():
                    self.delay_manager.increase_delay(name, 200)
                else:
                    self.delay_manager.increase_delay(name, 100)
            if any(c in str(e).lower() for c in ("429", "503", "403")):
                self.rate_limiter.handle_rate_limit(name)
            return []

    def search_smart(
        self,
        keyword: str,
        top_n: int = 8,
        domains: Optional[Set[str]] = None,
        precise_term: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
    ) -> List[str]:
        domain_key = (
            "_".join(sorted(domains)) if domains else "all"
        )
        cache_key = f"smart_{domain_key}_{keyword}_{precise_term or ''}".lower()
        cached = self.cache.get(cache_key)
        if cached:
            return cached[:top_n]

        allowed_ids: Optional[Set[str]] = None
        if domains:
            allowed_ids = set()
            with self.lock:
                for pname, pdomains in self.provider_domains.items():
                    if pdomains & domains:
                        allowed_ids.add(pname)
            if fallback_providers:
                allowed_ids.update(fallback_providers)

        sorted_providers = self._get_providers_sorted_by_performance(allowed_ids)
        if not sorted_providers:
            sorted_providers = self._get_providers_sorted_by_performance()

        sorted_providers = sorted_providers[: self.MAX_PROVIDERS_PER_SEARCH]

        if not sorted_providers:
            raise ImageProviderError("No image providers available")

        # #region agent log
        try:
            from .debug_log import dbg
            dbg(
                "image_providers.py:search_smart",
                "providers_selected",
                {
                    "keyword": keyword[:40],
                    "domains": sorted(domains) if domains else None,
                    "provider_names": [p[0] for p in sorted_providers],
                },
                "C",
            )
        except Exception:
            pass
        # #endregion

        all_scored: List[ImageScore] = []
        workers = min(self.max_workers, len(sorted_providers))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self._search_provider, p, keyword, precise_term
                ): p[0]
                for p in sorted_providers
            }
            for future in as_completed(futures, timeout=18):
                try:
                    all_scored.extend(future.result(timeout=8))
                except FuturesTimeoutError:
                    self.provider_stats[futures[future]].record_failure()
                except Exception as e:
                    logger.debug(f"search_smart future error: {e}")

        if not all_scored:
            raise ImageProviderError(f"No images found for: '{keyword}'")

        all_scored.sort(key=lambda x: x.score, reverse=True)
        top_urls = [img.url for img in all_scored[:top_n]]
        self.cache.set(cache_key, top_urls)
        return top_urls

    def get_best_image_url(
        self,
        keyword: str,
        domains: Optional[Set[str]] = None,
        precise_term: Optional[str] = None,
    ) -> Optional[str]:
        urls = self.search_smart(
            keyword, top_n=1, domains=domains, precise_term=precise_term
        )
        return urls[0] if urls else None
