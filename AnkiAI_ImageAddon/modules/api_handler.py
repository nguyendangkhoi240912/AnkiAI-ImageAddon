"""
API Handler Module v5.0 - Multi-AI + 20 image sources + domain routing + Imagen 4 Ultra
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

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
    ANIMATED_FALLBACK_PROVIDERS,
)
from .imagen_provider import (
    ImageGenerationPipeline,
    GeminiImageDescriber,
    ImagenProvider,
)
from .debug_log import dbg

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception cho API calls"""
    pass


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
        # Imagen 4 Ultra parameters
        imagen_enabled: bool = False,
        imagen_api_key: str = "",
        imagen_service_account_json: str = "",
        gemini_image_description_api_key: str = "",
        gemini_image_description_api_key_backup_1: str = "",
        gemini_image_description_api_key_backup_2: str = "",
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

        # Initialize Imagen 4 Ultra Generation Pipeline
        self.imagen_pipeline = None
        if imagen_enabled:
            try:
                gemini_desc_keys = [
                    k for k in [
                        gemini_image_description_api_key,
                        gemini_image_description_api_key_backup_1,
                        gemini_image_description_api_key_backup_2,
                    ]
                    if k and k.strip()
                ]
                
                if gemini_desc_keys and imagen_api_key:
                    self.imagen_pipeline = ImageGenerationPipeline(
                        gemini_api_keys=gemini_desc_keys,
                        imagen_api_key=imagen_api_key,
                        imagen_service_account=imagen_service_account_json,
                        enable_fallback_to_search=True
                    )
                    logger.info("Imagen 4 Ultra Generation Pipeline initialized")
                else:
                    logger.warning(
                        "Imagen enabled but missing API keys: "
                        f"gemini_desc_keys={len(gemini_desc_keys)}, "
                        f"imagen_key={bool(imagen_api_key)}"
                    )
            except Exception as e:
                logger.warning(f"Imagen pipeline initialization failed: {e}")

        self._result_url_cache: Dict[str, Tuple[str, float]] = {}

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
                dbg(
                    "api_handler.py:get_image_url",
                    "search_phase2_fallback",
                    {"domains": sorted(domains_fallback)},
                    "B",
                )
                candidate_urls = self.smart_selector.search_smart(
                    ctx.keyword,
                    top_n=top_n,
                    domains=domains_fallback,
                    precise_term=ctx.precise_term,
                    fallback_providers=FALLBACK_PROVIDERS,
                )

            if not candidate_urls:
                raise APIError(f"No images found for: '{ctx.keyword}'")

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
            )

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

    def get_animated_image_url(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> str:
        """Get animated GIF/image URL for vocabulary word.
        
        Uses the 'animated' domain to search only animated providers.
        """
        result_cache_key = f"animated_{vocabulary}|{definition}".lower()
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
                        keyword=keyword, domain="animated", precise_term=keyword
                    )
                self.context_cache.set(cache_key, ctx)
            except AIProviderError as e:
                raise APIError(f"Keyword generation failed: {e}")

        if not (self.enable_smart_selection and self.smart_selector):
            raise APIError("Image selection disabled")

        try:
            # Use animated domain
            domains_animated = {"animated"}
            
            candidate_urls = self.smart_selector.search_smart(
                ctx.keyword,
                top_n=1,
                domains=domains_animated,
                precise_term=ctx.precise_term,
                fallback_providers=ANIMATED_FALLBACK_PROVIDERS,
            )

            if not candidate_urls:
                raise APIError(f"No animated images found for: '{ctx.keyword}'")

            best_url = candidate_urls[0]
            self._set_result_cache(result_cache_key, best_url)
            return best_url

        except ImageProviderError as e:
            raise APIError(f"Animated image search failed: {e}")

    def generate_image_with_imagen(
        self, 
        vocabulary: str, 
        definition: str, 
        examples: str = "",
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic"
    ) -> Tuple[Optional[List[bytes]], str, Dict]:
        """
        Generate image using Imagen 4 Ultra with Gemini image description guidance.
        
        Pipeline:
        1. Gemini analyzes vocabulary + definition + examples
        2. Generates detailed image description
        3. Imagen creates image from description
        
        Args:
            vocabulary: English word
            definition: Word definition
            examples: Usage examples
            width: Image width
            height: Image height
            style: Image style (photorealistic, illustration, etc.)
        
        Returns:
            (image_bytes_list, provider_name, metadata_dict)
        """
        if not self.imagen_pipeline:
            raise APIError("Imagen pipeline not initialized")
        
        try:
            logger.info(f"[APIHandler] Generating image for '{vocabulary}' with Imagen...")
            images, provider, metadata = self.imagen_pipeline.generate_image_for_vocabulary(
                vocabulary=vocabulary,
                definition=definition,
                examples=examples,
                width=width,
                height=height,
                style=style
            )
            return images, provider, metadata
        except Exception as e:
            raise APIError(f"Imagen generation failed: {e}")

    def generate_image_smart(
        self,
        vocabulary: str,
        definition: str,
        examples: str = "",
        prefer_generated: bool = False,
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic"
    ) -> Tuple[Optional[str], str]:
        """
        Smart image retrieval: choose between search-based or AI-generated images.
        
        Args:
            vocabulary: English word
            definition: Word definition
            examples: Usage examples
            prefer_generated: Prefer AI-generated over search (if Imagen available)
            width: For generated images
            height: For generated images
            style: Image style for generated images
        
        Returns:
            (image_url_or_path, provider_type) where provider_type is "Search" or "Imagen"
        """
        if prefer_generated and self.imagen_pipeline:
            try:
                images, provider, metadata = self.generate_image_with_imagen(
                    vocabulary, definition, examples, width, height, style
                )
                if images and len(images) > 0:
                    # Save image locally and return path
                    logger.info(f"[APIHandler] Saving generated image for '{vocabulary}'...")
                    # TODO: Implement image saving to Anki media folder
                    return "[GENERATED_IMAGE]", "Imagen"
            except APIError as e:
                logger.warning(f"Imagen generation failed, falling back to search: {e}")
        
        # Fallback to search-based images
        try:
            url = self.get_image_url(vocabulary, definition, examples)
            return url, "Search"
        except APIError as e:
            raise APIError(f"Both Imagen and search failed: {e}")

    def is_imagen_available(self) -> bool:
        """Check if Imagen pipeline is available and healthy"""
        if not self.imagen_pipeline:
            return False
        return self.imagen_pipeline.generator.is_available()

    def get_imagen_stats(self) -> Dict:
        """Get Imagen generation statistics"""
        if not self.imagen_pipeline:
            return {}
        return {
            "generation_log_count": len(self.imagen_pipeline.generation_log),
            "provider_stats": self.imagen_pipeline.generator.get_stats()
        }
