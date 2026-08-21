"""
API Handler Module v5.3 - Multi-AI + 20 image sources + domain routing + optimized HTTP pooling
Performance optimizations: centralized connection pooling, caching, adaptive retry strategy
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple, Any

from .ai_providers import (
    MultiAIProvider,
    AIProviderError,
    GeminiImageEvaluator,
    SearchContext,
)
from .image_providers import ImageProviderError
from .provider_registry import (
    build_smart_selector,
    resolve_domains,
    FALLBACK_PROVIDERS,
)
from .debug_log import dbg, cursor_session_log

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception cho API calls"""
    pass


def _normalize_cache_text(value: str) -> str:
    """Normalize note text so formatting differences reuse the same API/cache result."""
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(text.split()).strip().lower()


class SearchContextCache:
    """Cache SearchContext JSON per vocabulary+definition.
    
    v5.3 Improvement: Reduced TTL from 24h to 4h for better cache freshness
    while still providing good hit rates (~80%)
    """

    def __init__(self, max_size: int = 1000, ttl_hours: int = 4):  # ⚡ Reduced from 24h
        from collections import OrderedDict
        import threading

        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self.lock = threading.Lock()
        logger.info(f"🚀 SearchContextCache initialized: max_size={max_size}, TTL={ttl_hours}h")

    def make_key(self, vocabulary: str, definition: str) -> str:
        return f"{_normalize_cache_text(vocabulary)}|{_normalize_cache_text(definition)}"

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
        # G2.3: track whether CLIP reranker is active for this instance
        self._enable_clip_reranker = bool(
            (provider_config or {}).get("enable_clip_reranker", False)
        )

        # G2.3: When CLIP reranker is enabled, skip Gemini image evaluator entirely.
        # enable_clip_reranker is passed in via provider_config (config key from GĐ2).
        _clip_reranker_active = bool(
            (provider_config or {}).get("enable_clip_reranker", False)
        )
        if _clip_reranker_active and enable_ai_evaluation:
            logger.info(
                "CLIP reranker active — skipping GeminiImageEvaluator init "
                "(enable_ai_evaluation overridden by enable_clip_reranker)"
            )
            enable_ai_evaluation = False

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
        self.prefer_fewer_api_calls = (
            provider_config.get("prefer_fewer_api_calls", True) if provider_config else True
        )
        self.max_eval_candidates = int(
            provider_config.get("max_eval_candidates", 2) if provider_config else 2
        )

        # Imagen support (v5.0)
        self.imagen_enabled = provider_config.get("imagen_enabled", False) if provider_config else False
        self.imagen_api_key = provider_config.get("imagen_api_key", "") if provider_config else ""
        if not self.imagen_api_key:
            self.imagen_api_key = gemini_key
        self.gemini_desc_keys = [
            provider_config.get("gemini_image_description_api_key", ""),
            provider_config.get("gemini_image_description_api_key_backup_1", ""),
            provider_config.get("gemini_image_description_api_key_backup_2", "")
        ] if provider_config else []
        self.gemini_desc_keys = [k for k in self.gemini_desc_keys if k and k.strip()]
        if not self.gemini_desc_keys and gemini_key:
            self.gemini_desc_keys = [
                gemini_key,
                gemini_backup_key or gemini_keyword_backup
            ]
            self.gemini_desc_keys = [k for k in self.gemini_desc_keys if k and k.strip()]
        self.imagen_service_account = provider_config.get("imagen_service_account_json", "") if provider_config else ""
        self.imagen_fallback_to_search = provider_config.get("imagen_fallback_to_search_providers", True) if provider_config else True
        self.imagen_default_style = provider_config.get("imagen_default_style", "photorealistic") if provider_config else "photorealistic"
        self.imagen_default_size = provider_config.get("imagen_default_size", "1024x1024") if provider_config else "1024x1024"

        self.pipeline = None
        self._generation_mode = (
            (provider_config or {}).get("image_generation_mode", "search")
        )
        # #region agent log
        cursor_session_log(
            "api_handler.py:AIImageProvider.__init__",
            "imagen_init_flags",
            {
                "imagen_enabled": bool(self.imagen_enabled),
                "has_imagen_key": bool(self.imagen_api_key),
                "gemini_desc_key_count": len(self.gemini_desc_keys),
                "generation_mode_cfg": self._generation_mode,
            },
            "A",
        )
        # #endregion
        need_pipeline = (
            self.imagen_enabled
            or self._generation_mode in ("generate", "smart")
        ) and self.imagen_api_key and self.gemini_desc_keys
        if need_pipeline:
            try:
                from .imagen_provider import ImageGenerationPipeline
                self.pipeline = ImageGenerationPipeline(
                    gemini_api_keys=self.gemini_desc_keys,
                    imagen_api_key=self.imagen_api_key,
                    imagen_service_account=self.imagen_service_account,
                    enable_fallback_to_search=self.imagen_fallback_to_search,
                    imagen_endpoint=(
                        (provider_config or {}).get("imagen_endpoint", "")
                    ),
                    imagen_timeout=int(
                        (provider_config or {}).get("imagen_timeout_seconds", 25)
                    ),
                    imagen_retries=int(
                        (provider_config or {}).get("imagen_request_retries", 2)
                    ),
                    enable_safety=bool(
                        (provider_config or {}).get(
                            "imagen_enable_safety_checking", True
                        )
                    ),
                )
                logger.info("✓ Imagen Generation Pipeline initialized in AIImageProvider")
            except Exception as e:
                logger.warning(f"Failed to initialize Imagen pipeline: {e}")
        # #region agent log
        cursor_session_log(
            "api_handler.py:AIImageProvider.__init__",
            "imagen_pipeline_state",
            {"pipeline_ready": self.pipeline is not None},
            "A",
        )
        # #endregion

    def get_image_url(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> str:
        result_cache_key = (
            "result_"
            f"{_normalize_cache_text(vocabulary)}|"
            f"{_normalize_cache_text(definition)}|"
            f"{_normalize_cache_text(examples)}"
        )
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
            if self.enable_ai_evaluation and self.image_evaluator:
                top_n = (
                    min(self.max_eval_candidates, 2)
                    if self.prefer_fewer_api_calls
                    else min(self.max_eval_candidates, 5)
                )
            else:
                top_n = 1

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

            candidate_urls = self._dedupe_urls(candidate_urls)
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

            # G2.3: If CLIP reranker is active, use it instead of Gemini eval.
            _clip_active = getattr(self, "_enable_clip_reranker", False)
            if _clip_active and len(candidate_urls) > 1:
                try:
                    from AnkiAI_ImageAddon.modules.classification.clip_scorer import get_clip_scorer
                    from AnkiAI_ImageAddon.modules.reranker import rerank
                    from AnkiAI_ImageAddon.image_providers.base_provider import Candidate
                    _cands = [
                        Candidate(url=u, provider="unknown", visual_type="photo")
                        for u in candidate_urls
                    ]
                    class _MinVerdict:
                        group = "A"
                        en_query = vocabulary
                    _ranked = rerank(_cands, _MinVerdict(), get_clip_scorer())
                    best_url = _ranked[0].url
                except Exception as _clip_err:
                    logger.warning(f"CLIP reranker failed: {_clip_err} — using first result")
                    best_url = candidate_urls[0]
            elif len(candidate_urls) == 1 or not (
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
        return self._dedupe_urls(self._last_candidate_urls[1:8])

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

    @staticmethod
    def _dedupe_urls(urls: List[str]) -> List[str]:
        seen = set()
        unique = []
        for url in urls:
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(url)
        return unique

    def get_imagen_blockers(self) -> List[str]:
        """Reasons Imagen cannot run (empty list = OK for generate mode)."""
        blockers = []
        if not self.imagen_api_key:
            blockers.append("Thiếu Imagen API Key (Google AI Studio)")
        if not self.gemini_desc_keys:
            blockers.append(
                "Thiếu Gemini mô tả ảnh — cần ít nhất Key chính trong Cài đặt nâng cao"
            )
        if blockers:
            return blockers
        if not self.pipeline:
            blockers.append(
                "Pipeline Imagen không khởi tạo được — kiểm tra API key và khởi động lại Anki"
            )
        return blockers

    def generate_image_with_imagen(
        self,
        vocabulary: str,
        definition: str,
        examples: str = "",
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic"
    ) -> Tuple[Optional[List[bytes]], str, Dict]:
        """Tạo ảnh bằng Imagen 4 Ultra"""
        # #region agent log
        cursor_session_log(
            "api_handler.py:generate_image_with_imagen",
            "entry",
            {
                "pipeline_ready": self.pipeline is not None,
                "imagen_enabled": bool(self.imagen_enabled),
                "vocab_len": len(vocabulary or ""),
            },
            "A",
        )
        # #endregion
        if not self.pipeline:
            raise APIError("Imagen pipeline is not initialized or enabled")

        try:
            out = self.pipeline.generate_image_for_vocabulary(
                vocabulary=vocabulary,
                definition=definition,
                examples=examples,
                width=width,
                height=height,
                style=style
            )
            # #region agent log
            img_count = len(out[0]) if out and out[0] else 0
            cursor_session_log(
                "api_handler.py:generate_image_with_imagen",
                "success",
                {"image_count": img_count, "provider": out[1] if len(out) > 1 else ""},
                "B",
            )
            # #endregion
            return out
        except Exception as e:
            # #region agent log
            cursor_session_log(
                "api_handler.py:generate_image_with_imagen",
                "exception",
                {"error_type": type(e).__name__, "error": str(e)[:300]},
                "B",
            )
            # #endregion
            logger.error(f"Error in generate_image_with_imagen: {e}")
            raise APIError(f"Imagen generation failed: {e}")

    def generate_image_smart(
        self,
        vocabulary: str,
        definition: str,
        examples: str = "",
        prefer_generated: bool = True,
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic"
    ) -> Tuple[Optional[Any], str]:
        """
        Chọn tự động: search-based vs generated.
        Trả về: (url_or_bytes, source)
        """
        if prefer_generated and self.pipeline and (self.imagen_enabled or self._generation_mode in ("generate", "smart")):
            try:
                logger.info(f"Smart selection: trying Imagen generation first for '{vocabulary}'...")
                images, provider_name, metadata = self.generate_image_with_imagen(
                    vocabulary=vocabulary,
                    definition=definition,
                    examples=examples,
                    width=width,
                    height=height,
                    style=style
                )
                if images and len(images) > 0:
                    return images[0], "Imagen"
                logger.info("Imagen returned no images, falling back to search providers...")
            except Exception as e:
                logger.warning(f"Imagen generation failed during smart selection: {e}. Falling back to search...")

        # Fallback to traditional search
        logger.info(f"Smart selection: searching for '{vocabulary}'...")
        url = self.get_image_url(vocabulary, definition, examples)
        return url, "Search"

    def is_imagen_available(self) -> bool:
        """Kiểm tra health của Imagen"""
        if not self.pipeline or not self.pipeline.generator:
            return False
        return self.pipeline.generator.is_available()

    def get_imagen_stats(self) -> Dict:
        """Lấy thống kê sử dụng của Imagen"""
        if not self.pipeline or not self.pipeline.generator:
            return {}
        return {
            "provider_stats": self.pipeline.generator.get_stats(),
            "generation_log": self.pipeline.generation_log
        }
