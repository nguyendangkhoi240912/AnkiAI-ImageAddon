"""
API Handler Module v5.0 - Multi-AI + 20 image sources + domain routing
Performance optimizations: connection pooling, caching, retry strategy
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests

from .ai_providers import (
    MultiAIProvider,
    AIProviderError,
    GeminiImageEvaluator,
)
from .image_providers import ImageProviderError
from .provider_registry import (
    build_smart_selector,
    resolve_domains,
    FALLBACK_PROVIDERS,
)
from .debug_log import dbg

logger = logging.getLogger(__name__)


# ✨ PERFORMANCE: Connection pooling + retry strategy (v5.1)
def _create_session_with_retry():
    """Create requests.Session with automatic retry strategy for rate limits"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Global session - reuse across all requests (reduces connection overhead ~30%)
_requests_session = _create_session_with_retry()


# ✨ URL CACHING - Cache image URLs to avoid duplicate searches (v5.1)
class URLCache:
    """LRU cache for image URLs"""
    def __init__(self, max_size: int = 1000):
        from collections import OrderedDict
        import threading
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[str]:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            self.cache[key] = value
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

_url_cache = URLCache()


class APIError(Exception):
    """Exception cho API calls"""
    pass


class SearchContext:
    """Encapsulates search context with keyword, domain, and precise term"""
    
    def __init__(self, keyword: str, domain: str, precise_term: str):
        self.keyword = keyword
        self.domain = domain
        self.precise_term = precise_term
    
    def to_json(self) -> str:
        """Convert to JSON string for caching"""
        import json
        return json.dumps({
            "keyword": self.keyword,
            "domain": self.domain,
            "precise_term": self.precise_term,
        })
    
    @staticmethod
    def from_json(json_str: str) -> "SearchContext":
        """Create SearchContext from JSON string"""
        import json
        data = json.loads(json_str)
        return SearchContext(
            keyword=data["keyword"],
            domain=data["domain"],
            precise_term=data["precise_term"],
        )


class SearchContextCache:
    """Cache SearchContext JSON per vocabulary+definition."""

    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        from collections import OrderedDict
        import threading

        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self.lock = threading.Lock()

    def make_key(self, vocabulary: str, definition: str) -> str:
        return f"{vocabulary}|{definition}".lower()

    def get(self, key: str) -> Optional[SearchContext]:
        import time as _time

        with self.lock:
            if key not in self.cache:
                return None
            raw, timestamp = self.cache[key]
            if _time.time() - timestamp >= self.ttl_seconds:
                del self.cache[key]
                return None
            return SearchContext.from_json(raw)

    def set(self, key: str, ctx: SearchContext):
        import time as _time

        with self.lock:
            if key in self.cache:
                del self.cache[key]
            self.cache[key] = (ctx.to_json(), _time.time())
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)


class AIImageProvider:
    """Wrapper cho Multi-AI + Smart Image Selection v5.0"""

    def __init__(
        self,
        gemini_key: str = "",
        gemini_backup_key: str = "",
        gemini_keyword_backup: str = "",
        gemini_eval_api_key_1: str = "",
        gemini_eval_api_key_2: str = "",
        gemini_eval_api_key_3: str = "",
        gemini_eval_api_key_4: str = "",
        gemini_eval_api_key_5: str = "",
        gemini_eval_api_key_6: str = "",
        gemini_eval_api_key_7: str = "",
        groq_key: str = "",
        use_ollama: bool = False,
        ollama_url: str = "http://localhost:11434",
        provider_config: Optional[Dict] = None,
        enable_smart_selection: bool = True,
        enable_ai_evaluation: bool = True,
        enable_ai_provider_routing: bool = True,
        enable_rate_limit_protection: bool = True,
        max_concurrent_providers: int = 10,
        enable_adaptive_delay: bool = True,
        base_delay_ms: int = 100,
        max_delay_ms: int = 2000,
    ):
        try:
            self.ai_provider = MultiAIProvider(
                gemini_key=gemini_key,
                gemini_backup_key=gemini_keyword_backup or gemini_backup_key,
                groq_key=groq_key,
                use_ollama=use_ollama,
                ollama_url=ollama_url,
            )
        except AIProviderError as e:
            raise APIError(f"AI Provider failed: {e}")

        self.context_cache = SearchContextCache(max_size=1000)
        self.enable_ai_provider_routing = enable_ai_provider_routing
        self.enable_ai_evaluation = enable_ai_evaluation
        self.enable_smart_selection = enable_smart_selection

        self.image_evaluator = None
        if enable_ai_evaluation:
            eval_keys = [
                k
                for k in (
                    gemini_eval_api_key_1,
                    gemini_eval_api_key_2,
                    gemini_eval_api_key_3,
                    gemini_eval_api_key_4,
                    gemini_eval_api_key_5,
                    gemini_eval_api_key_6,
                    gemini_eval_api_key_7,
                )
                if k and k.strip()
            ]
            if eval_keys:
                try:
                    self.image_evaluator = GeminiImageEvaluator(eval_keys)
                except AIProviderError as e:
                    logger.warning(f"Image Evaluator init failed: {e}")

        self.smart_selector = None
        if enable_smart_selection and provider_config:
            try:
                self.smart_selector = build_smart_selector(
                    provider_config,
                    enable_adaptive_delay=enable_adaptive_delay,
                    base_delay_ms=base_delay_ms,
                    max_delay_ms=max_delay_ms,
                )
            except ImageProviderError as e:
                raise APIError(str(e))

        self._result_url_cache: Dict[str, Tuple[str, float]] = {}
        self._last_candidate_urls: List[str] = []

    def get_image_url(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> str:
        result_cache_key = f"result_{vocabulary}|{definition}".lower()
        cached_url = self._get_result_cache(result_cache_key)
        if cached_url:
            return cached_url

        cache_key = self.context_cache.make_key(vocabulary, definition)
        ctx = self.context_cache.get(cache_key)

        if not ctx:
            try:
                if self.enable_ai_provider_routing:
                    ctx, _ = self.ai_provider.generate_search_context(
                        vocabulary, definition, examples
                    )
                else:
                    keyword, _ = self.ai_provider.generate_keyword(
                        vocabulary, definition, examples
                    )
                    ctx = SearchContext(
                        keyword=keyword, domain="general", precise_term=keyword
                    )
                self.context_cache.set(cache_key, ctx)
            except AIProviderError as e:
                raise APIError(f"Keyword generation failed: {e}")

        if not (self.enable_smart_selection and self.smart_selector):
            raise APIError("Image selection disabled")

        try:
            top_n = 5 if (self.enable_ai_evaluation and self.image_evaluator) else 1

            # Phase 1: domain-specific providers only (avoid general stock photos)
            domains_primary = resolve_domains(
                ctx.domain,
                self.enable_ai_provider_routing,
                include_general_fallback=False,
            )
            # #region agent log
            dbg(
                "api_handler.py:get_image_url",
                "search_phase1",
                {
                    "domain": ctx.domain,
                    "keyword": ctx.keyword,
                    "precise_term": ctx.precise_term,
                    "domains": sorted(domains_primary),
                },
                "B",
            )
            # #endregion

            candidate_urls = self.smart_selector.search_smart(
                ctx.keyword,
                top_n=top_n,
                domains=domains_primary,
                precise_term=ctx.precise_term,
            )

            # Phase 2: fallback to general providers if domain-specific search empty
            if not candidate_urls and ctx.domain != "general":
                domains_fallback = resolve_domains(
                    ctx.domain,
                    self.enable_ai_provider_routing,
                    include_general_fallback=True,
                )
                # #region agent log
                dbg(
                    "api_handler.py:get_image_url",
                    "search_phase2_fallback",
                    {"domains": sorted(domains_fallback)},
                    "B",
                )
                # #endregion
                candidate_urls = self.smart_selector.search_smart(
                    ctx.keyword,
                    top_n=top_n,
                    domains=domains_fallback,
                    precise_term=ctx.precise_term,
                    fallback_providers=FALLBACK_PROVIDERS,
                )

            if not candidate_urls:
                raise APIError(f"No images found for: '{ctx.keyword}'")

            self._last_candidate_urls = list(candidate_urls)

            # #region agent log
            dbg(
                "api_handler.py:get_image_url",
                "search_done",
                {
                    "count": len(candidate_urls),
                    "top_url": candidate_urls[0][:100],
                    "top_provider_hint": candidate_urls[0].split("/")[2]
                    if candidate_urls
                    else "",
                },
                "B",
                run_id="post-fix",
            )
            # #endregion

            if len(candidate_urls) == 1 or not (
                self.enable_ai_evaluation and self.image_evaluator
            ):
                best_url = candidate_urls[0]
            else:
                try:
                    best_url = self.image_evaluator.evaluate_images(
                        candidate_urls, vocabulary, definition
                    )
                except AIProviderError as e:
                    logger.warning(f"Gemini evaluation failed: {e}")
                    best_url = candidate_urls[0]

            self._set_result_cache(result_cache_key, best_url)
            return best_url

        except ImageProviderError as e:
            raise APIError(f"Image search failed: {e}")

    def get_fallback_image_urls(self) -> List[str]:
        """Remaining candidate URLs after the primary choice (for download retry)."""
        return list(self._last_candidate_urls[1:8])

    def _get_result_cache(self, key: str) -> Optional[str]:
        entry = self._result_url_cache.get(key)
        if not entry:
            return None
        url, timestamp = entry
        if time.time() - timestamp > 43200:
            del self._result_url_cache[key]
            return None
        return url

    def _set_result_cache(self, key: str, url: str):
        self._result_url_cache[key] = (url, time.time())
        if len(self._result_url_cache) > 500:
            oldest = min(self._result_url_cache, key=lambda k: self._result_url_cache[k][1])
            del self._result_url_cache[oldest]
