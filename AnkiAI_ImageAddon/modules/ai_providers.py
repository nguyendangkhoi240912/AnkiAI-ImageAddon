"""
AI Providers Module v5.5 - Multi-provider AI integration with Gemini, Groq, Ollama
Auto-fallback when API is limited or fails
Centralized HTTP session management for optimal connection pooling

v5.5 Bug Fixes & Optimizations:
- Fix _update_provider_score double-0.1 multiplier (boost was capped at 0.001)
- Fix fallback_log race condition (now protected by lock)
- Fix GeminiProvider.is_available() wrong HTTP method (GET → HEAD/lightweight POST)
- Fix GeminiProvider.generate_search_context() unsafe nested key access
- Remove redundant _sort_providers_by_performance() call in __init__
- Add GeminiImageEvaluator._maybe_unblock_keys() to clear stale 429 blocks
- Auto-unblock rate-limited keys after KEY_BLOCK_TTL_SECONDS
"""

import requests
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from abc import ABC, abstractmethod
import threading
import time  # For performance tracking
from datetime import datetime

# 🚀 v5.3: Use centralized HTTP session manager (BUG-6: replaced duplicate _SessionManager)
from .http_session_manager import HTTPSessionManager

# Configure logging
logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Exception cho AI provider calls"""
    pass


VALID_IMAGE_DOMAINS = frozenset({
    "general",
    "medical",
    "chemistry",
    "biology",
    "taxonomy",
    "dermatology",
    "space",
    "math",
    "animated",
})


@dataclass
class SearchContext:
    """AI-routed search context for image providers v5.0."""
    keyword: str
    domain: str = "general"
    precise_term: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "keyword": self.keyword,
                "domain": self.domain,
                "precise_term": self.precise_term or self.keyword,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> "SearchContext":
        try:
            data = json.loads(raw)
            domain = data.get("domain", "general")
            if domain not in VALID_IMAGE_DOMAINS:
                domain = "general"
            keyword = data.get("keyword", "")
            precise = data.get("precise_term", keyword)
            return cls(keyword=keyword, domain=domain, precise_term=precise)
        except (json.JSONDecodeError, TypeError):
            return cls(keyword=raw.strip(), domain="general", precise_term=raw.strip())


# BUG-6 FIX: Removed duplicate _SessionManager class.
# All AI providers now use the centralized HTTPSessionManager from http_session_manager.py
# This eliminates a second connection pool and ensures proper cleanup on addon unload.


class AIProvider(ABC):
    """Base class cho tất cả AI providers"""
    
    @abstractmethod
    def generate_keyword(self, vocabulary: str, definition: str, examples: str = "") -> str:
        """Generate search keyword từ vocabulary + definition + examples"""
        pass

    @abstractmethod
    def generate_search_context(self, vocabulary: str, definition: str, examples: str = "") -> SearchContext:
        """Generate SearchContext with domain routing từ vocabulary + definition + examples"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Kiểm tra xem provider có sẵn sàng không"""
        pass


# Smart prompt template for all AI providers
SMART_KEYWORD_PROMPT = """You are an expert at finding the PERFECT stock photo for vocabulary flashcards.

Word: {vocabulary}
Definition: {definition}
{examples_section}
Your task: Generate the BEST 2-3 word English search query to find a clear, memorable photo on stock photo sites (Pexels, Unsplash, Pixabay).

Rules:
1. Think about what VISUAL IMAGE best represents this word's meaning
2. Be SPECIFIC and CONCRETE - avoid abstract words
3. For abstract concepts, think of a real-world SCENE or OBJECT that represents it
4. For verbs, describe the ACTION being performed
5. For adjectives, describe an OBJECT that clearly shows that quality
6. Prefer common, photogenic subjects that stock photos would have
7. Use the provided examples as context for better visual representation

Examples of good queries:
- "procrastinate" → "person distracted phone"
- "resilience" → "tree growing rock"
- "abundant" → "overflowing fruit basket"
- "negotiate" → "business handshake meeting"
- "erosion" → "eroded cliff coastline"
- "melancholy" → "person rainy window"

Respond with ONLY the search query, nothing else."""


def _format_examples(examples: str) -> str:
    """Format examples section for prompt (optional)"""
    if not examples or not examples.strip():
        return ""
    # Remove HTML tags and clean up
    examples_clean = examples.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    examples_clean = re.sub(r"<[^>]+>", "", examples_clean).strip()
    if examples_clean:
        return f"Examples of usage: {examples_clean}\n"
    return ""

def _clean_keyword(raw: str) -> str:
    """Clean AI response to extract just the search keyword"""
    # Remove quotes
    keyword = raw.strip().strip('"').strip("'").strip('`')
    # Remove markdown formatting
    keyword = re.sub(r'\*+', '', keyword)
    # Take only first line
    keyword = keyword.split('\n')[0].strip()
    # Remove common prefixes AI might add
    # 🚀 Optimize: Lowercase once instead of per-iteration
    keyword_lower = keyword.lower()
    prefixes = ('search query:', 'query:', 'keywords:', 'keyword:')
    for prefix in prefixes:
        if keyword_lower.startswith(prefix):
            keyword = keyword[len(prefix):].strip()
            keyword_lower = keyword.lower()  # Update for next iteration
            break  # Found match, no need to check others
    # Limit to max 4 words
    words = keyword.split()
    if len(words) > 4:
        keyword = ' '.join(words[:4])
    return keyword


SEARCH_CONTEXT_PROMPT = """You route vocabulary flashcards to the best image search APIs.

Word: {vocabulary}
Definition: {definition}
{examples_section}
Return ONE line of JSON only (no markdown):
{{"domain": "<domain>", "keyword": "<2-4 English words for image search>", "precise_term": "<exact scientific name, formula, species, or drug name if applicable; else same as keyword>"}}

domain must be one of: general, medical, chemistry, biology, taxonomy, dermatology, space, math, animated

Rules:
- general: everyday vocabulary, language learning, common objects
- medical: anatomy, physiology, pathology, clinical terms
- chemistry: chemical compounds, drugs, molecular structures
- biology: cells, proteins, molecular biology, microbiology
- taxonomy: species, genera, evolutionary biology (use Latin names in precise_term when known)
- dermatology: skin lesions, rashes, melanoma, clinical dermatology
- space: astronomy, planets, NASA-style topics
- math: equations, physics formulas (put LaTeX in precise_term when applicable)
- animated: cute illustrations, cartoons, emojis, animated GIFs
"""


def _parse_search_context(raw: str, vocabulary: str) -> SearchContext:
    """Parse AI JSON response into SearchContext with safe fallbacks."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            domain = data.get("domain", "general")
            if domain not in VALID_IMAGE_DOMAINS:
                domain = "general"
            keyword = _clean_keyword(str(data.get("keyword", vocabulary)))
            precise = str(data.get("precise_term", keyword)).strip() or keyword
            if len(precise.split()) > 8:
                precise = " ".join(precise.split()[:8])
            return SearchContext(keyword=keyword, domain=domain, precise_term=precise)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    kw = _clean_keyword(text) or vocabulary
    return SearchContext(keyword=kw, domain="general", precise_term=kw)


class GeminiProvider(AIProvider):
    """Google Gemini API Provider - Miễn phí, chất lượng cao - v4.2 with fallback"""
    
    def __init__(self, api_key: str, backup_key: str = "", backup_key_2: str = ""):
        """Khởi tạo Gemini provider with fallback keys"""
        # Tạo fallback chain
        self.api_keys = [key.strip() for key in [api_key, backup_key, backup_key_2] if key and key.strip()]
        
        if not self.api_keys:
            raise AIProviderError("Gemini API key không được cấu hình")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-3.5-flash-lite"
        self.name = "Gemini"
        # BUG-6 FIX: Use centralized HTTPSessionManager instead of duplicate _SessionManager
        self.session = HTTPSessionManager.get_session("gemini")
    
    def is_available(self) -> bool:
        """Kiểm tra nhanh Gemini có khả dụng.

        Gửi một POST tối thiểu (maxOutputTokens=1) để xác nhận key hợp lệ.
        HTTP 200 = hợp lệ và model đáp ứng.
        HTTP 400 = key hợp lệ nhưng request thiếu field (expected ở endpoint POST).
        """
        for api_key in self.api_keys:
            try:
                response = self.session.post(
                    f"{self.base_url}/{self.model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": "x"}]}],
                        "generationConfig": {"maxOutputTokens": 1},
                    },
                    timeout=3,
                )
                if response.status_code in (200, 400):
                    return True
            except Exception as e:
                logger.debug(f"Gemini availability check failed: {e}")
                continue
        return False
    
    def generate_keyword(self, vocabulary: str, definition: str, examples: str = "") -> str:
        """Generate search keyword bằng Gemini with fallback keys"""
        examples_section = _format_examples(examples)
        prompt = SMART_KEYWORD_PROMPT.format(
            vocabulary=vocabulary,
            definition=definition,
            examples_section=examples_section
        )
        
        last_error = None
        for api_key in self.api_keys:
            try:
                response = self.session.post(
                    f"{self.base_url}/{self.model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.5,
                            "maxOutputTokens": 30
                        }
                    },
                    timeout=8  # ⚡ Tối ưu từ 10s xuống 8s
                )
                
                if response.status_code != 200:
                    last_error = response.json().get("error", {}).get("message", response.text)
                    continue  # Try next key
                
                result = response.json()
                
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        keyword = _clean_keyword(candidate["content"]["parts"][0]["text"])
                        return keyword
                
                last_error = "Empty response"
                continue
            
            except requests.exceptions.Timeout:
                last_error = "Timeout (8s)"
                continue
            except requests.exceptions.ConnectionError:
                last_error = "Connection failed"
                continue
            except Exception as e:
                last_error = str(e)
                continue
        
        # All keys failed
        raise AIProviderError(f"All Gemini keys failed: {last_error}")

    def generate_search_context(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> SearchContext:
        examples_section = _format_examples(examples)
        prompt = SEARCH_CONTEXT_PROMPT.format(
            vocabulary=vocabulary,
            definition=definition,
            examples_section=examples_section,
        )
        last_error = None
        for api_key in self.api_keys:
            try:
                response = self.session.post(
                    f"{self.base_url}/{self.model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 120,
                        },
                    },
                    timeout=10,
                )
                if response.status_code != 200:
                    try:
                        last_error = response.json().get("error", {}).get("message", response.text)
                    except ValueError:
                        last_error = response.text
                    continue
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    try:
                        text = candidates[0]["content"]["parts"][0]["text"]
                        return _parse_search_context(text, vocabulary)
                    except (KeyError, IndexError, TypeError) as e:
                        last_error = f"Malformed response: {e}"
                        continue
                last_error = "Empty candidates"
            except Exception as e:
                last_error = str(e)
        raise AIProviderError(f"Gemini search context failed: {last_error}")


class GroqProvider(AIProvider):
    """Groq API Provider - Miễn phí, siêu nhanh"""
    
    def __init__(self, api_key: str):
        """Khởi tạo Groq provider"""
        if not api_key or api_key.strip() == "":
            raise AIProviderError("Groq API key không được cấu hình")
        
        self.api_key = api_key.strip()
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama-3.1-8b-instant"
        self.name = "Groq"
        # BUG-6 FIX: Use centralized HTTPSessionManager
        self.session = HTTPSessionManager.get_session("groq")
    
    def is_available(self) -> bool:
        """Kiểm tra nhanh Groq có khả dụng"""
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "x"}],
                    "max_tokens": 5
                },
                timeout=3  # ⚡ Timeout ngắn cho kiểm tra
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Groq availability check failed: {e}")
            return False
    
    def generate_keyword(self, vocabulary: str, definition: str, examples: str = "") -> str:
        """Generate search keyword bằng Groq - SIÊU NHANH"""
        examples_section = _format_examples(examples)
        prompt = SMART_KEYWORD_PROMPT.format(
            vocabulary=vocabulary,
            definition=definition,
            examples_section=examples_section
        )
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a stock photo search expert. Respond with ONLY the search query."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.5,
                    "max_tokens": 30
                },
                timeout=5  # ⚡ Groq siêu nhanh, timeout 5s là đủ
            )
            
            if response.status_code != 200:
                error_msg = response.json().get("error", {}).get("message", response.text)
                raise AIProviderError(f"Groq API error: {error_msg}")
            
            keyword = _clean_keyword(response.json()["choices"][0]["message"]["content"])
            return keyword
        
        except requests.exceptions.Timeout:
            raise AIProviderError("Groq timeout (5s)")
        except requests.exceptions.ConnectionError:
            raise AIProviderError("Groq: Connection failed")
        except Exception as e:
            raise AIProviderError(f"Groq error: {str(e)}")

    def generate_search_context(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> SearchContext:
        examples_section = _format_examples(examples)
        prompt = SEARCH_CONTEXT_PROMPT.format(
            vocabulary=vocabulary,
            definition=definition,
            examples_section=examples_section,
        )
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Respond with ONE line of JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 120,
                },
                timeout=8,
            )
            if response.status_code != 200:
                raise AIProviderError(f"Groq API error: {response.text}")
            text = response.json()["choices"][0]["message"]["content"]
            return _parse_search_context(text, vocabulary)
        except Exception as e:
            raise AIProviderError(f"Groq search context failed: {str(e)}")


class OllamaProvider(AIProvider):
    """Ollama Local Provider - Hoàn toàn miễn phí"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """Khởi tạo Ollama provider"""
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.name = "Ollama"
        # BUG-6 FIX: Use centralized HTTPSessionManager
        self.session = HTTPSessionManager.get_session("ollama")
    
    def is_available(self) -> bool:
        """Kiểm tra nhanh Ollama có chạy"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=2  # ⚡ Timeout rất ngắn cho local
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False
    
    def generate_keyword(self, vocabulary: str, definition: str, examples: str = "") -> str:
        """Generate search keyword bằng Ollama (local)"""
        examples_section = _format_examples(examples)
        prompt = SMART_KEYWORD_PROMPT.format(
            vocabulary=vocabulary,
            definition=definition,
            examples_section=examples_section
        )
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.5
                },
                timeout=15  # ⚡ Local có thể chậm hơn
            )
            
            if response.status_code != 200:
                raise AIProviderError(f"Ollama error: {response.text}")
            
            result = response.json()
            keyword = _clean_keyword(result.get("response", ""))
            
            if not keyword:
                raise AIProviderError("Ollama: Empty response")
            
            return keyword
        
        except requests.exceptions.Timeout:
            raise AIProviderError("Ollama timeout (15s)")
        except requests.exceptions.ConnectionError:
            raise AIProviderError("Ollama: Not running")
        except Exception as e:
            raise AIProviderError(f"Ollama error: {str(e)}")

    def generate_search_context(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> SearchContext:
        examples_section = _format_examples(examples)
        prompt = SEARCH_CONTEXT_PROMPT.format(
            vocabulary=vocabulary,
            definition=definition,
            examples_section=examples_section,
        )
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                },
                timeout=15
            )
            if response.status_code != 200:
                raise AIProviderError(f"Ollama error: {response.text}")
            result = response.json()
            text = result.get("response", "")
            return _parse_search_context(text, vocabulary)
        except Exception as e:
            raise AIProviderError(f"Ollama search context failed: {str(e)}")


class MultiAIProvider:
    """
    Wrapper để dùng multiple AI providers với auto-fallback - v4.3 OPTIMIZED
    Features:
    - Provider performance tracking
    - Intelligent provider ordering
    - Smart provider selection
    - Reduced latency with caching
    """
    
    def __init__(self, gemini_key: str = "", groq_key: str = "", 
                 use_ollama: bool = False, ollama_url: str = "http://localhost:11434",
                 gemini_backup_key: str = ""):
        """Khởi tạo Multi-AI provider với performance tracking"""
        self.providers: List[Tuple[str, AIProvider]] = []
        self.provider_scores: Dict[str, float] = {}  # ✨ NEW: Provider performance scores
        self.fallback_log = []
        self.lock = threading.Lock()
        
        # BUG-9 FIX: Lazy availability check — don't make HTTP requests at Anki startup.
        # Providers are added without checking availability; first actual call will detect failures.
        # Thứ tự ưu tiên: Groq (nhanh nhất) -> Gemini -> Ollama (fallback cuối)
        
        # 1. Groq - Siêu nhanh (try first - fastest)
        if groq_key and groq_key.strip():
            try:
                provider = GroqProvider(groq_key)
                self.providers.append(("Groq", provider))
                self.provider_scores["Groq"] = 1.0  # Highest priority (fastest)
                logger.info("Groq provider registered")
            except AIProviderError as e:
                logger.warning(f"Groq initialization failed: {e}")
        
        # 2. Gemini - Chất lượng cao
        if gemini_key and gemini_key.strip():
            try:
                backup_keys = [b.strip() for b in [gemini_backup_key] if b and b.strip()]
                provider = GeminiProvider(gemini_key, *backup_keys)
                self.providers.append(("Gemini", provider))
                self.provider_scores["Gemini"] = 0.8  # Second priority
                logger.info("Gemini provider registered")
            except AIProviderError as e:
                logger.warning(f"Gemini initialization failed: {e}")
        
        # 3. Ollama - Local backup (try last - potential latency)
        if use_ollama:
            try:
                provider = OllamaProvider(ollama_url)
                self.providers.append(("Ollama", provider))
                self.provider_scores["Ollama"] = 0.5  # Lowest priority
                logger.info("Ollama provider registered")
            except AIProviderError as e:
                logger.warning(f"Ollama initialization failed: {e}")
        
        if not self.providers:
            raise AIProviderError(
                "Không có AI provider nào được cấu hình! "
                "Vui lòng cấu hình ít nhất một API key (Gemini hoặc Groq)"
            )
        # NOTE: No initial sort needed — _providers_by_performance() re-sorts dynamically
    
    def _sort_providers_by_performance(self):
        """Sort providers by performance score - ✨ NEW v4.3"""
        with self.lock:
            self.providers.sort(
                key=lambda p: self.provider_scores.get(p[0], 0.5),
                reverse=True
            )

    def _providers_by_performance(self) -> List[Tuple[str, AIProvider]]:
        """Return a sorted snapshot without mutating provider order on each score update."""
        with self.lock:
            return sorted(
                self.providers,
                key=lambda p: self.provider_scores.get(p[0], 0.5),
                reverse=True,
            )
    
    def _update_provider_score(self, provider_name: str, success: bool, response_time: float = 0):
        """Update provider performance score.

        Bug fix v5.5: removed double-0.1 multiplier that capped max boost at 0.001.
        Now boost ranges 0–0.1 based on response speed (fast response = higher boost).
        """
        with self.lock:
            current_score = self.provider_scores.get(provider_name, 0.5)
            if success:
                # Boost 0–0.1 depending on speed (0s = +0.1, 10s+ = +0.0)
                boost = max(0.0, 0.1 * (1.0 - min(response_time, 10.0) / 10.0))
                new_score = min(1.0, current_score + boost)
            else:
                # Penalise failures
                new_score = max(0.1, current_score - 0.2)
            self.provider_scores[provider_name] = new_score
    
    def generate_keyword(self, vocabulary: str, definition: str, examples: str = "") -> Tuple[str, str]:
        """
        Generate search keyword với auto-fallback.
        - Tries fastest provider first (sorted by performance score)
        - Updates provider scores based on success/failure

        Returns:
            Tuple (keyword, provider_name)
        """
        with self.lock:
            self.fallback_log = []
        
        # ✨ Get providers sorted by current performance
        providers_to_try = self._providers_by_performance()
        
        for provider_name, provider in providers_to_try:
            try:
                start_time = time.time()
                logger.info(f"[{provider_name}] Generating keyword for '{vocabulary}'...")
                keyword = provider.generate_keyword(vocabulary, definition, examples)
                response_time = time.time() - start_time
                
                # ✨ Update provider score on success
                self._update_provider_score(provider_name, True, response_time)
                
                logger.info(f"[✓] {provider_name} success: '{keyword}' ({response_time:.2f}s)")
                return keyword, provider_name
            
            except AIProviderError as e:
                error_msg = str(e)
                self.fallback_log.append(f"{provider_name}: {error_msg}")
                
                # ✨ Update provider score on failure
                self._update_provider_score(provider_name, False)
                
                logger.warning(f"[✗] {provider_name} failed, trying next... ({error_msg})")
                continue
        
        # Tất cả providers đều failed
        error_summary = "\n".join(self.fallback_log)
        raise AIProviderError(
            f"Tất cả AI providers đều thất bại:\n{error_summary}"
        )

    def generate_search_context(
        self, vocabulary: str, definition: str, examples: str = ""
    ) -> Tuple[SearchContext, str]:
        """Generate SearchContext with domain routing."""
        with self.lock:
            self.fallback_log = []
        providers_to_try = self._providers_by_performance()
        for provider_name, provider in providers_to_try:
            try:
                start_time = time.time()
                ctx = provider.generate_search_context(
                    vocabulary, definition, examples
                )
                response_time = time.time() - start_time
                self._update_provider_score(provider_name, True, response_time)
                logger.info(
                    f"[✓] {provider_name} context: domain={ctx.domain} "
                    f"keyword='{ctx.keyword}' ({response_time:.2f}s)"
                )
                return ctx, provider_name
            except AIProviderError as e:
                self.fallback_log.append(f"{provider_name}: {e}")
                self._update_provider_score(provider_name, False)
                continue
        error_summary = "\n".join(self.fallback_log)
        raise AIProviderError(
            f"Tất cả AI providers đều thất bại:\n{error_summary}"
        )
    
    def get_fallback_log(self) -> List[str]:
        """Lấy log của quá trình fallback"""
        return self.fallback_log


class GeminiImageEvaluator:
    """
    Gemini Embedding API để đánh giá ảnh - v5.5 EMBEDDING-BASED SELECTION
    - Gemini Embedding 2 (gemini-embedding-exp-03-07) làm primary model
    - Gemini Embedding 1 (text-embedding-004) làm fallback
    - Cosine similarity để chọn ảnh phù hợp nhất với từ vựng
    - 7 API keys với auto-failover
    - Time-based auto-unblock: keys bị block do 429 sẽ được unblock sau KEY_BLOCK_TTL_SECONDS
    """

    # Seconds after which a rate-limited key is eligible for retry
    KEY_BLOCK_TTL_SECONDS = 300  # 5 minutes

    # Model tier: primary -> fallback
    EMBEDDING_MODELS = [
        "gemini-embedding-exp-03-07",   # Gemini Embedding 2
        "text-embedding-004",            # Gemini Embedding 1 (fallback)
    ]

    def __init__(self, api_keys: List[str]):
        """
        Khởi tạo Gemini Image Evaluator với 7 API keys

        Args:
            api_keys: List của 7 API keys (hoặc ít hơn nếu không cấu hình đủ)
        """
        self.api_keys = [key.strip() for key in api_keys if key and key.strip()]

        if not self.api_keys:
            raise AIProviderError("At least one Gemini API key required for image evaluation")

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = self.EMBEDDING_MODELS[0]   # Gemini Embedding 2
        self.name = "GeminiImageEvaluator"
        self.session = HTTPSessionManager.get_session("gemini_eval")

        # 🚀 Track API key status for intelligent failover
        self.api_key_status = {}
        for i, key in enumerate(self.api_keys):
            key_id = f"key_{i+1}"
            self.api_key_status[key_id] = {
                "key": key,
                "blocked": False,
                "failure_count": 0,
                "last_failure_time": None,
                "consecutive_429_count": 0
            }

        self.fallback_log = []

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _maybe_unblock_keys(self) -> None:
        """Unblock keys whose block TTL has expired.

        Called at the start of each evaluate_images() so stale 429 blocks
        from previous calls don't permanently degrade the key pool.
        """
        now = datetime.now()
        for key_id, status in self.api_key_status.items():
            if status["blocked"] and status["last_failure_time"]:
                elapsed = (now - status["last_failure_time"]).total_seconds()
                if elapsed >= self.KEY_BLOCK_TTL_SECONDS:
                    status["blocked"] = False
                    status["consecutive_429_count"] = 0
                    msg = f"[UNBLOCK] {key_id}: TTL expired ({elapsed:.0f}s), re-enabling"
                    self.fallback_log.append(msg)
                    logger.info(f"[🔓 EVALUATOR] {msg}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mark_key_blocked(self, key_id: str, reason: str):
        """Đánh dấu API key bị khoá"""
        self.api_key_status[key_id]["blocked"] = True
        self.api_key_status[key_id]["last_failure_time"] = datetime.now()
        log_msg = f"[BLOCKED] {key_id}: {reason}"
        self.fallback_log.append(log_msg)
        logger.warning(f"[⚠️ GEMINI EVALUATOR] {log_msg}")

    def _get_available_key(self) -> Tuple[str, str]:
        """
        Lấy API key có sẵn (không bị khoá)
        Returns: (key_id, api_key) hoặc raise nếu tất cả bị khoá
        """
        for key_id, status in self.api_key_status.items():
            if not status["blocked"]:
                return (key_id, status["key"])

        # Nếu tất cả bị khoá, thử reset những key cũ
        now = datetime.now()
        for key_id, status in self.api_key_status.items():
            if status["last_failure_time"]:
                elapsed = (now - status["last_failure_time"]).total_seconds()
                if elapsed > 300:   # Reset sau 5 phút
                    status["blocked"] = False
                    status["consecutive_429_count"] = 0
                    log_msg = f"[RESET] {key_id}: Tìm lại sau khoảng thời gian"
                    self.fallback_log.append(log_msg)
                    return (key_id, status["key"])

        raise AIProviderError("Tất cả Gemini API keys đều bị khoá - vui lòng kiểm tra lại")

    def _is_blocking_error(self, status_code: int, response_text: str) -> bool:
        """Kiểm tra nếu đây là lỗi khoá API (429, 403, etc.)"""
        if status_code in (429, 403, 401):
            return True
        response_lower = response_text.lower()
        return any(err in response_lower for err in ('quota', 'blocked', 'forbidden'))

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Tính cosine similarity giữa hai embedding vectors"""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = sum(a * a for a in vec_a) ** 0.5
        mag_b = sum(b * b for b in vec_b) ** 0.5
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)

    @staticmethod
    def _url_to_text(url: str) -> str:
        """
        Chuyển URL ảnh thành text mô tả để embed.
        Trích xuất filename (không có extension) và thay dấu _ / - bằng dấu cách.
        """
        try:
            # Lấy phần cuối URL sau dấu /
            path = url.split("?")[0].rstrip("/")
            filename = path.split("/")[-1]
            # Bỏ extension
            name = filename.rsplit(".", 1)[0] if "." in filename else filename
            # Chuẩn hoá
            name = re.sub(r"[_\-]+", " ", name)
            return name.strip() or url
        except Exception:
            return url

    def _embed_text(
        self, text: str, api_key: str, model: str
    ) -> Tuple[Optional[List[float]], int]:
        """
        Gọi Gemini Embedding API để lấy embedding vector.

        Returns:
            (vector, status_code)
            vector là None nếu thất bại; status_code để phân biệt rate-limit vs lỗi khác.
        """
        try:
            response = self.session.post(
                f"{self.base_url}/{model}:embedContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "model": f"models/{model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": "SEMANTIC_SIMILARITY",
                },
                timeout=10,
            )
            if response.status_code != 200:
                return None, response.status_code
            data = response.json()
            vec = data.get("embedding", {}).get("values")
            return vec, 200
        except requests.exceptions.Timeout:
            logger.warning(f"[Embedding] {model} timeout")
            return None, 408
        except requests.exceptions.ConnectionError:
            logger.warning(f"[Embedding] {model} connection error")
            return None, 503
        except Exception as e:
            logger.warning(f"[Embedding] _embed_text error: {e}")
            return None, 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_images(
        self,
        candidate_urls: List[str],
        vocabulary: str,
        definition: str,
        examples: str = "",
    ) -> str:
        """
        Đánh giá danh sách ảnh, trả về URL ảnh có cosine similarity cao nhất
        với từ vựng + định nghĩa.

        Luồng failover:
          Với mỗi API key:
            1. Thử Gemini Embedding 2 (gemini-embedding-exp-03-07)
            2. Nếu rate limit (429) → thử Gemini Embedding 1 (text-embedding-004) cùng key
            3. Nếu cả 2 đều rate limit → chuyển sang API key tiếp theo
          Sau khi hết tất cả API keys:
            → Rate Limit Protection: chờ rồi unblock tất cả keys, thử lại từ đầu
        """
        if not candidate_urls:
            raise AIProviderError("No candidate URLs provided")

        if len(candidate_urls) == 1:
            return candidate_urls[0]

        # Auto-unblock keys whose TTL has expired before starting
        self._maybe_unblock_keys()

        # Xây dựng query text từ vocabulary + definition + examples
        query_parts = [vocabulary, definition]
        if examples and examples.strip():
            query_parts.append(examples.strip())
        query_text = " | ".join(filter(None, query_parts))

        # Xây dựng image text list một lần (tránh lặp lại)
        image_texts = [self._url_to_text(u) for u in candidate_urls]

        # Rate Limit Protection: tối đa 2 vòng (lần 1 + 1 lần retry sau khi chờ)
        MAX_RETRY_ROUNDS = 2
        RATE_LIMIT_WAIT_SECONDS = 60

        for retry_round in range(MAX_RETRY_ROUNDS):
            if retry_round > 0:
                # ⏳ Rate Limit Protection: chờ rồi unblock toàn bộ keys
                logger.warning(
                    f"[🛡️ RATE LIMIT PROTECTION] Tất cả API keys đều bị rate limit. "
                    f"Chờ {RATE_LIMIT_WAIT_SECONDS}s rồi thử lại từ key đầu tiên..."
                )
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
                # Unblock tất cả keys để thử lại
                for s in self.api_key_status.values():
                    s["blocked"] = False
                    s["consecutive_429_count"] = 0
                self.fallback_log.append(
                    f"[RATE_LIMIT_PROTECTION] Round {retry_round+1}: unblocked all keys"
                )

            all_rate_limited = True  # Giả sử tất cả bị rate limit cho đến khi có key không bị

            for key_id, status in self.api_key_status.items():
                if status["blocked"]:
                    continue

                api_key = status["key"]
                all_rate_limited = False  # Có ít nhất 1 key chưa bị block

                # ── Inner loop: thử từng model theo thứ tự tier ──────────────
                model_rate_limited_count = 0

                for model in self.EMBEDDING_MODELS:
                    logger.info(
                        f"[Embedding] {key_id} → {model} (round {retry_round+1})..."
                    )

                    # 1. Embed query text
                    query_vec, q_status = self._embed_text(query_text, api_key, model)

                    if q_status == 429:
                        # Rate limit cho model này → thử model tiếp theo (cùng key)
                        status["consecutive_429_count"] += 1
                        model_rate_limited_count += 1
                        logger.warning(
                            f"[⚠️ RATE LIMIT] {key_id}/{model} bị rate limit, "
                            f"thử model tiếp theo..."
                        )
                        self.fallback_log.append(
                            f"[RATE_LIMIT] {key_id}/{model} → next model"
                        )
                        continue

                    if query_vec is None:
                        # Lỗi không phải rate limit (model không hỗ trợ, timeout, etc.)
                        status["failure_count"] += 1
                        logger.warning(
                            f"[❌] {key_id}/{model} lỗi (status={q_status}), thử model tiếp..."
                        )
                        continue

                    # 2. Embed từng ảnh và tính cosine similarity
                    best_idx = 0
                    best_score = -1.0
                    embed_failed = False

                    for i, img_text in enumerate(image_texts):
                        img_vec, img_status = self._embed_text(img_text, api_key, model)

                        if img_status == 429:
                            # Rate limit giữa chừng → bỏ model này
                            status["consecutive_429_count"] += 1
                            model_rate_limited_count += 1
                            logger.warning(
                                f"[⚠️ RATE LIMIT] {key_id}/{model} rate limit khi embed ảnh #{i+1}"
                            )
                            embed_failed = True
                            break

                        if img_vec is None:
                            logger.debug(f"[Embedding] Bỏ qua ảnh #{i+1} (embed thất bại)")
                            continue

                        score = self._cosine_similarity(query_vec, img_vec)
                        logger.debug(
                            f"[Embedding] Ảnh #{i+1} '{img_text[:40]}' similarity={score:.4f}"
                        )
                        if score > best_score:
                            best_score = score
                            best_idx = i

                    if embed_failed:
                        # Rate limit giữa chừng → thử model tiếp theo
                        self.fallback_log.append(
                            f"[RATE_LIMIT] {key_id}/{model} → next model (mid-embed)"
                        )
                        continue

                    # ✅ Thành công
                    log_msg = (
                        f"[✅] {key_id}/{model}: Chọn ảnh #{best_idx+1} "
                        f"(similarity={best_score:.4f})"
                    )
                    self.fallback_log.append(log_msg)
                    logger.info(f"[🎯 EVALUATOR] {log_msg}")
                    return candidate_urls[best_idx]

                # ── Sau khi thử hết models cho key này ───────────────────────
                if model_rate_limited_count == len(self.EMBEDDING_MODELS):
                    # Tất cả models đều rate limit → block key, chuyển sang key tiếp theo
                    self._mark_key_blocked(
                        key_id,
                        f"Tất cả embedding models đều rate limit (429)"
                    )
                    status["consecutive_429_count"] += 1
                    logger.info(
                        f"[🔄 FAILOVER] {key_id} bị rate limit hoàn toàn → chuyển key tiếp theo..."
                    )
                else:
                    # Có lỗi nhưng không phải rate limit → block key (lỗi thật)
                    self._mark_key_blocked(
                        key_id,
                        f"Embedding thất bại với các models"
                    )

            if all_rate_limited:
                # Tất cả keys đều bị block ngay từ đầu vòng lặp
                # → sẽ kích hoạt Rate Limit Protection ở vòng tiếp theo
                continue

            # Nếu đã thử hết keys mà không thành công, thoát vòng retry
            break

        # Tất cả vòng thử đều thất bại → dùng ảnh đầu tiên làm fallback
        logger.error(
            "[⚠️ EVALUATOR] Tất cả API keys và models đều thất bại. "
            "Dùng ảnh đầu tiên làm fallback."
        )
        self.fallback_log.append("[FALLBACK] Dùng ảnh đầu tiên")
        return candidate_urls[0]

    def get_status_report(self) -> str:
        """Lấy báo cáo trạng thái của tất cả API keys"""
        report = f"📊 Gemini Image Evaluator Status (model: {self.model}):\n"
        for key_id, status in self.api_key_status.items():
            blocked_status = "🔴 BLOCKED" if status["blocked"] else "🟢 ACTIVE"
            report += f"{key_id}: {blocked_status} (Failures: {status['failure_count']})\n"
        return report

