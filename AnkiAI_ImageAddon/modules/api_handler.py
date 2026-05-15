"""
API Handler Module v4.5 - Multi-AI + Smart Image Selection
Optimizations:
- Reduced redundant API calls
- Aggressive timeouts (Groq: 5s, Gemini: 8s, Images: 4-5s)
- Early cache hits skip all processing
- Fallback chain with minimal overhead
- Memory-efficient result handling
- Multi-key Gemini backup system
- Rate-limit auto-pause protection
"""

import requests
import json
import logging
from typing import Optional, Dict, List, Tuple
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from .ai_providers import MultiAIProvider, AIProviderError, GeminiImageEvaluator
from .image_providers import (
    SmartImageSelector, 
    PexelsProvider, 
    UnsplashProvider, 
    OpenverseProvider,
    LoremPicsumProvider,
    LibraryOfCongressProvider,
    WikimediaCommonsProvider,
    MetMuseumProvider,
    EuropeanaProvider,
    ImageProviderError
)

# Configure logging
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception cho API calls"""
    pass


class KeywordCache:
    """
    Cache cho keywords để tránh re-call AI - v4.3 ULTRA-OPTIMIZED
    🚀 Optimizations:
    - OrderedDict for O(1) FIFO eviction (vs O(n) min scan)
    - Reduced lock contention (check TTL outside lock)
    - CPython dict is thread-safe for reads
    - Fast O(1) access with minimal synchronization
    - Automatic TTL cleanup
    """
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        from collections import OrderedDict
        self.cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()  # 🚀 O(1) FIFO
        self.max_size = max_size
        self.ttl_seconds = ttl_hours * 3600
        self.lock = __import__('threading').Lock()
        self.access_count = 0  # ✨ Track access for cleanup
    
    def get(self, key: str) -> Optional[str]:
        """Lấy keyword từ cache - O(1) ULTRA-FAST"""
        import time
        
        # Quick check outside lock
        if key not in self.cache:
            return None
        
        # Safe read with lock
        with self.lock:
            if key not in self.cache:  # Double-check inside lock
                return None
            
            value, timestamp = self.cache[key]
            
            # Check TTL
            elapsed = time.time() - timestamp
            if elapsed >= self.ttl_seconds:
                del self.cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: str):
        """Lưu keyword vào cache - 🚀 O(1) FIFO eviction"""
        import time
        
        with self.lock:
            # Remove if exists to maintain insertion order
            if key in self.cache:
                del self.cache[key]
            
            # Add to end
            self.cache[key] = (value, time.time())
            
            # 🚀 O(1) FIFO eviction using OrderedDict.popitem(last=False)
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove oldest (first) entry
    
    def clear(self):
        """Xóa toàn bộ cache"""
        with self.lock:
            self.cache.clear()
            self.access_count = 0
    
    def size(self) -> int:
        """Lấy số items trong cache"""
        with self.lock:
            return len(self.cache)
    
    def make_key(self, vocabulary: str, definition: str) -> str:
        """Tạo cache key từ vocabulary + definition"""
        # ✨ Simplified key generation for speed
        return f"{vocabulary}|{definition}".lower()



class AIImageProvider:
    """
    Wrapper cho Multi-AI + Smart Image Selection - v4.0
    Optimized for performance, quality, and reliability
    """
    
    def __init__(self, 
                 # AI Providers (v4.2 - multi-key)
                 gemini_key: str = "", 
                 gemini_backup_key: str = "",
                 gemini_keyword_backup: str = "",  # ✨ NEW v4.2
                 # 🆕 v4.4: 7 Gemini Image Evaluator API keys with auto-failover
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
                 # Image Search Providers (v4.2 - expanded)
                 unsplash_key: str = None, 
                 pexels_key: str = None,
                 europeana_key: str = None,  # ✨ NEW v4.2
                 # Settings (v4.2)
                 enable_smart_selection: bool = True,
                 enable_ai_evaluation: bool = True,  # ✨ v4.4: Re-enabled with 7 keys
                 enable_rate_limit_protection: bool = True,  # ✨ NEW v4.2
                 max_concurrent_providers: int = 6,
                 # ✨ NEW v4.3: Adaptive delay settings
                 enable_adaptive_delay: bool = True,
                 base_delay_ms: int = 100,
                 max_delay_ms: int = 2000):
        """
        Khởi tạo AIImageProvider với 15+ image providers + 7-key Gemini Image Evaluation
        
        Args:
            gemini_key: Main Gemini API key (keyword generation)
            gemini_backup_key: Gemini backup API key (v4.0)
            gemini_keyword_backup: Backup for keyword gen (v4.2)
            gemini_eval_api_key_1-7: Gemini Image Evaluator API keys (v4.4 - 7 keys with auto-failover)
            groq_key, use_ollama: Other AI providers
            unsplash_key, pexels_key: Image provider keys
            europeana_key: New provider (v4.2)
            enable_smart_selection: Use SmartImageSelector
            enable_ai_evaluation: Use Gemini Vision to pick best image (v4.4 - re-enabled with 7 keys)
            enable_rate_limit_protection: Auto-pause on rate limit (v4.2)
            max_concurrent_providers: Max concurrent provider requests
        """
        # Initialize AI Provider
        try:
            self.ai_provider = MultiAIProvider(
                gemini_key=gemini_key,
                gemini_backup_key=gemini_keyword_backup or gemini_backup_key,  # ✨ v4.2
                groq_key=groq_key,
                use_ollama=use_ollama,
                ollama_url=ollama_url
            )
            logger.info("AI Provider initialized successfully")
        except AIProviderError as e:
            raise APIError(f"AI Provider failed: {e}")
        
        # Initialize keyword cache
        self.keyword_cache = KeywordCache(max_size=1000)
        
        # 🆕 v4.4: Initialize Gemini Image Evaluator with 7 API keys + auto-failover
        self.image_evaluator = None
        self.enable_ai_evaluation = enable_ai_evaluation
        
        if enable_ai_evaluation:
            # Collect 7 API keys (in priority order)
            eval_keys = [
                gemini_eval_api_key_1,
                gemini_eval_api_key_2,
                gemini_eval_api_key_3,
                gemini_eval_api_key_4,
                gemini_eval_api_key_5,
                gemini_eval_api_key_6,
                gemini_eval_api_key_7
            ]
            
            # Filter out empty keys
            eval_keys = [k for k in eval_keys if k and k.strip()]
            
            if eval_keys:
                try:
                    self.image_evaluator = GeminiImageEvaluator(eval_keys)
                    logger.info(f"Gemini Image Evaluator initialized with {len(eval_keys)} API keys")
                except AIProviderError as e:
                    logger.warning(f"Image Evaluator init failed: {e}, will use fast-path selection only")
                    self.image_evaluator = None
        
        # Initialize Smart Image Selector (v4.2 + v4.3 adaptive delay)
        self.smart_selector = None
        self.enable_smart_selection = enable_smart_selection
        
        if enable_smart_selection:
            # ✨ NEW v4.3: Pass adaptive delay settings
            self.smart_selector = SmartImageSelector(
                max_workers=max_concurrent_providers,
                enable_adaptive_delay=enable_adaptive_delay,
                base_delay_ms=base_delay_ms,
                max_delay_ms=max_delay_ms
            )
            
            # Add providers to smart selector (priority order)
            if pexels_key:
                try:
                    self.smart_selector.add_provider(
                        "pexels", 
                        PexelsProvider(pexels_key)
                    )
                except Exception as e:
                    logger.warning(f"Pexels init failed: {e}")
            
            if unsplash_key:
                try:
                    self.smart_selector.add_provider(
                        "unsplash", 
                        UnsplashProvider(unsplash_key)
                    )
                except Exception as e:
                    logger.warning(f"Unsplash init failed: {e}")
            
            # Free providers (no API key needed!)
            try:
                self.smart_selector.add_provider(
                    "openverse", 
                    OpenverseProvider()
                )
            except Exception as e:
                logger.warning(f"Openverse init failed: {e}")
            
            # Lorem Picsum (instant, NO API key!)
            try:
                self.smart_selector.add_provider(
                    "lorem_picsum", 
                    LoremPicsumProvider()
                )
            except Exception as e:
                logger.warning(f"Lorem Picsum init failed: {e}")
            
            # ✨ NEW v4.2: Additional Providers
            
            # Library of Congress (FREE - Public domain)
            try:
                self.smart_selector.add_provider(
                    "loc",
                    LibraryOfCongressProvider()
                )
            except Exception as e:
                logger.warning(f"Library of Congress init failed: {e}")
            
            # Wikimedia Commons (FREE - Wikipedia media)
            try:
                self.smart_selector.add_provider(
                    "wikimedia",
                    WikimediaCommonsProvider()
                )
            except Exception as e:
                logger.warning(f"Wikimedia Commons init failed: {e}")
            
            # Metropolitan Museum (FREE - Art collection)
            try:
                self.smart_selector.add_provider(
                    "metmuseum",
                    MetMuseumProvider()
                )
            except Exception as e:
                logger.warning(f"Met Museum init failed: {e}")
            
            # Europeana (if key provided - European cultural heritage)
            if europeana_key:
                try:
                    self.smart_selector.add_provider(
                        "europeana",
                        EuropeanaProvider(europeana_key)
                    )
                except Exception as e:
                    logger.warning(f"Europeana init failed: {e}")
            
            if not self.smart_selector.providers:
                raise APIError("Không có image provider nào được cấu hình!")
            
            logger.info(f"Smart Image Selector initialized with {len(self.smart_selector.providers)} providers")
    
    def get_image_url(self, vocabulary: str, definition: str, examples: str = "") -> str:
        """
        Lấy URL ảnh tốt nhất - v4.6 with examples context
        
        Flow:
        1. Check full result cache (FASTEST - O(1) direct return) ✨ NEW
        2. Check keyword cache (FAST - O(1))
        3. Generate keyword từ AI (with fallback chain)
        4. Search images concurrently (all providers in parallel)
        5. Gemini Image Evaluation with 7-key failover (if enabled)
        6. Cache result for future calls ✨ NEW
        """
        # ⚡ ULTRA-FAST-PATH: Check if we have complete result cached
        result_cache_key = f"result_{vocabulary}|{definition}".lower()
        if hasattr(self, '_result_cache'):
            cached_result = self._result_cache.get(result_cache_key)
            if cached_result:
                return cached_result
        else:
            # ✨ Initialize result cache on first use
            self._result_cache = KeywordCache(max_size=500)
        
        # ⚡ STEP 1: Try keyword cache
        cache_key = self.keyword_cache.make_key(vocabulary, definition)
        cached_keyword = self.keyword_cache.get(cache_key)
        
        if cached_keyword:
            keyword = cached_keyword
        else:
            # STEP 2: Generate keyword từ AI
            try:
                keyword, provider_name = self.ai_provider.generate_keyword(
                    vocabulary, 
                    definition,
                    examples
                )
                self.keyword_cache.set(cache_key, keyword)
            except AIProviderError as e:
                raise APIError(f"Keyword generation failed: {e}")
        
        # ⚡ STEP 3: Smart image search (concurrent, with timeout)
        if not (self.enable_smart_selection and self.smart_selector):
            raise APIError("Image selection disabled")
        
        try:
            # 🆕 v4.4: Collect multiple candidates for evaluation
            top_n = 5 if (self.enable_ai_evaluation and self.image_evaluator) else 1
            candidate_urls = self.smart_selector.search_smart(keyword, top_n=top_n)
            
            if not candidate_urls:
                raise APIError(f"No images found for: '{keyword}'")
            
            # 🆕 STEP 4: Gemini Image Evaluation with 7-key auto-failover (if enabled)
            if len(candidate_urls) == 1 or not (self.enable_ai_evaluation and self.image_evaluator):
                best_url = candidate_urls[0]
            else:
                # Multiple candidates - use Gemini to pick the best
                try:
                    best_url = self.image_evaluator.evaluate_images(
                        candidate_urls,
                        vocabulary,
                        definition
                    )
                except AIProviderError as e:
                    # Fallback: return first from search
                    logger.warning(f"Gemini evaluation failed: {e}, using first match")
                    best_url = candidate_urls[0]
            
            # ✨ Cache the full result for future calls
            self._result_cache.set(result_cache_key, best_url)
            return best_url
        
        except ImageProviderError as e:
            raise APIError(f"Image search failed: {e}")

