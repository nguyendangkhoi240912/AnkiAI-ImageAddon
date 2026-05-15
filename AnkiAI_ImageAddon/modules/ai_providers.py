"""
AI Providers Module - Multi-provider AI integration with Gemini, Groq, Ollama
Auto-fallback when API is limited or fails

v4.5 Optimizations:
- Request pooling & session reuse (HTTP keep-alive)
- Aggressive timeout tuning (Groq: 5s, Gemini: 8s)
- Response streaming for large outputs
- Lazy session initialization
- Memory-efficient caching
- Proper logging instead of prints
"""

import requests
import json
import logging
import re
from typing import Optional, List, Tuple, Dict
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
import time  # For performance tracking
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Exception cho AI provider calls"""
    pass


# ⚡ Global session manager for connection pooling
class _SessionManager:
    """Manage HTTP sessions with connection pooling"""
    _sessions = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_session(cls, name: str = "default") -> requests.Session:
        """Get or create a session with connection pooling"""
        with cls._lock:
            if name not in cls._sessions:
                session = requests.Session()
                # Connection pooling
                adapter = HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=10,
                    max_retries=Retry(total=2, backoff_factor=0.1)
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                cls._sessions[name] = session
            return cls._sessions[name]


class AIProvider(ABC):
    """Base class cho tất cả AI providers"""
    
    @abstractmethod
    def generate_keyword(self, vocabulary: str, definition: str, examples: str = "") -> str:
        """Generate search keyword từ vocabulary + definition + examples"""
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


class GeminiProvider(AIProvider):
    """Google Gemini API Provider - Miễn phí, chất lượng cao - v4.2 with fallback"""
    
    def __init__(self, api_key: str, backup_key: str = "", backup_key_2: str = ""):
        """Khởi tạo Gemini provider with fallback keys"""
        # Tạo fallback chain
        self.api_keys = [key.strip() for key in [api_key, backup_key, backup_key_2] if key and key.strip()]
        
        if not self.api_keys:
            raise AIProviderError("Gemini API key không được cấu hình")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.5-flash"
        self.name = "Gemini"
        self.session = _SessionManager.get_session("gemini")
    
    def is_available(self) -> bool:
        """Kiểm tra nhanh Gemini có khả dụng"""
        for api_key in self.api_keys:
            try:
                response = self.session.get(
                    f"{self.base_url}/{self.model}:generateContent",
                    params={"key": api_key},
                    timeout=3  # ⚡ Tối ưu timeout
                )
                if response.status_code == 400:
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
        self.session = _SessionManager.get_session("groq")
    
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


class OllamaProvider(AIProvider):
    """Ollama Local Provider - Hoàn toàn miễn phí"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """Khởi tạo Ollama provider"""
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.name = "Ollama"
        self.session = _SessionManager.get_session("ollama")
    
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
        
        # Thứ tự ưu tiên: Groq (nhanh nhất) -> Gemini -> Ollama (fallback cuối)
        
        # 1. Groq - Siêu nhanh (try first - fastest)
        if groq_key and groq_key.strip():
            try:
                provider = GroqProvider(groq_key)
                if provider.is_available():
                    self.providers.append(("Groq", provider))
                    self.provider_scores["Groq"] = 1.0  # ✨ Highest priority (fastest)
                    logger.info("Groq provider initialized")
                else:
                    logger.warning("Groq API key invalid")
            except AIProviderError as e:
                logger.warning(f"Groq initialization failed: {e}")
        
        # 2. Gemini - Chất lượng cao
        if gemini_key and gemini_key.strip():
            try:
                # ✨ NEW: Try with both backup and primary key
                backup_keys = [b.strip() for b in [gemini_backup_key] if b and b.strip()]
                provider = GeminiProvider(gemini_key, *backup_keys)
                if provider.is_available():
                    self.providers.append(("Gemini", provider))
                    self.provider_scores["Gemini"] = 0.8  # ✨ Second priority
                    logger.info("Gemini provider initialized")
                else:
                    logger.warning("Gemini API key invalid")
            except AIProviderError as e:
                logger.warning(f"Gemini initialization failed: {e}")
        
        # 3. Ollama - Local backup (try last - potential latency)
        if use_ollama:
            try:
                provider = OllamaProvider(ollama_url)
                if provider.is_available():
                    self.providers.append(("Ollama", provider))
                    self.provider_scores["Ollama"] = 0.5  # ✨ Lowest priority (local, variable)
                    logger.info("Ollama provider initialized")
                else:
                    logger.warning(f"Ollama server not running at {ollama_url}")
            except AIProviderError as e:
                logger.warning(f"Ollama initialization failed: {e}")
        
        if not self.providers:
            raise AIProviderError(
                "Không có AI provider nào được cấu hình! "
                "Vui lòng cấu hình ít nhất một API key (Gemini hoặc Groq)"
            )
        
        # ✨ Sort providers by performance score (fastest first)
        self._sort_providers_by_performance()
    
    def _sort_providers_by_performance(self):
        """Sort providers by performance score - ✨ NEW v4.3"""
        with self.lock:
            self.providers.sort(
                key=lambda p: self.provider_scores.get(p[0], 0.5),
                reverse=True
            )
    
    def _update_provider_score(self, provider_name: str, success: bool, response_time: float = 0):
        """Update provider performance score - ✨ NEW v4.3"""
        with self.lock:
            current_score = self.provider_scores.get(provider_name, 0.5)
            if success:
                # Boost score for successful fast responses
                boost = max(0, 0.1 * (1 - min(response_time, 10) / 10))
                new_score = min(1.0, current_score + boost * 0.1)
            else:
                # Penalize for failures
                new_score = max(0.1, current_score - 0.2)
            self.provider_scores[provider_name] = new_score
            
            # Re-sort after score update
            self.providers.sort(
                key=lambda p: self.provider_scores.get(p[0], 0.5),
                reverse=True
            )
    
    def generate_keyword(self, vocabulary: str, definition: str) -> Tuple[str, str]:
        """
        Generate search keyword với auto-fallback - v4.3 OPTIMIZED
        - Tries fastest provider first
        - Updates provider scores based on success/failure
        - Intelligent fallback
        
        Args:
            vocabulary: Từ vựng tiếng Anh
            definition: Định nghĩa
        
        Returns:
            Tuple (keyword, provider_name)
        """
        self.fallback_log = []
        
        # ✨ Get providers sorted by current performance
        with self.lock:
            providers_to_try = list(self.providers)
        
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
    
    def get_fallback_log(self) -> List[str]:
        """Lấy log của quá trình fallback"""
        return self.fallback_log


class GeminiImageEvaluator:
    """
    Gemini Vision API để đánh giá ảnh - v4.4 MEGA FAILOVER
    - 7 API keys với auto-failover
    - Tự động chuyển sang API tiếp theo khi bị khoá
    - Smart error detection & handling
    - Rate limit protection
    """
    
    def __init__(self, api_keys: List[str]):
        """
        Khởi tạo Gemini Image Evaluator với 7 API keys
        
        Args:
            api_keys: List của 7 API keys (hoặc ít hơn nếu không cấu hình đủ)
        """
        # Lọc và chuẩn hoá API keys
        self.api_keys = [key.strip() for key in api_keys if key and key.strip()]
        
        if not self.api_keys:
            raise AIProviderError("At least one Gemini API key required for image evaluation")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.5-flash"
        self.name = "GeminiImageEvaluator"
        self.session = _SessionManager.get_session("gemini_eval")
        
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
        # Ưu tiên keys không bị khoá
        for key_id, status in self.api_key_status.items():
            if not status["blocked"]:
                return (key_id, status["key"])
        
        # Nếu tất cả bị khoá, thử reset những key cũ
        now = datetime.now()
        for key_id, status in self.api_key_status.items():
            if status["last_failure_time"]:
                elapsed = (now - status["last_failure_time"]).total_seconds()
                if elapsed > 300:  # Reset sau 5 phút
                    status["blocked"] = False
                    status["consecutive_429_count"] = 0
                    log_msg = f"[RESET] {key_id}: Tìm lại sau khoảng thời gian"
                    self.fallback_log.append(log_msg)
                    return (key_id, status["key"])
        
        raise AIProviderError("Tất cả Gemini API keys đều bị khoá - vui lòng kiểm tra lại")
    
    def _is_blocking_error(self, status_code: int, response_text: str) -> bool:
        """Kiểm tra nếu đây là lỗi khoá API (429, 403, etc.)"""
        if status_code == 429:
            return True  # Rate limited
        if status_code == 403:
            return True  # Forbidden / Invalid key
        if status_code == 401:
            return True  # Unauthorized
        # 🚀 Optimize: Single lowercase operation instead of 3x
        response_lower = response_text.lower()
        if any(err in response_lower for err in ('quota', 'blocked', 'forbidden')):
            return True
        return False
    
    def evaluate_images(self, candidate_urls: List[str], vocabulary: str, definition: str, examples: str = "") -> str:
        """
        Đánh giá danh sách ảnh, trả về URL ảnh tốt nhất
        Với auto-failover qua 7 API keys
        """
        if not candidate_urls:
            raise AIProviderError("No candidate URLs provided")
        
        if len(candidate_urls) == 1:
            return candidate_urls[0]
        
        # Compact prompt để giảm token usage
        prompt = f"Select best image for '{vocabulary}' ({definition}).\nImages: "
        for i, url in enumerate(candidate_urls, 1):
            prompt += f"{i}. {url} "
        prompt += f"\nReply with ONLY number (1-{len(candidate_urls)})."
        
        # 🔄 Thử từng API key cho đến khi thành công
        last_error = None
        for key_id, status in self.api_key_status.items():
            # Bỏ qua keys bị khoá
            if status["blocked"]:
                continue
            
            api_key = status["key"]
            
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
                            "temperature": 0.1,
                            "maxOutputTokens": 3
                        }
                    },
                    timeout=10
                )
                
                # ⚠️ Kiểm tra lỗi khoá
                if response.status_code != 200:
                    response_text = response.text
                    
                    # Nếu là lỗi khoá, đánh dấu key này
                    if self._is_blocking_error(response.status_code, response_text):
                        reason = f"HTTP {response.status_code}"
                        self._mark_key_blocked(key_id, reason)
                        status["consecutive_429_count"] += 1
                        
                        # Thử key tiếp theo
                        logger.info(f"[🔄 FAILOVER] Key này bị khoá, chuyển sang key khác...")
                        continue
                    
                    last_error = response.text
                    continue
                
                # ✅ Thành công - parse kết quả
                result = response.json()
                
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        response_text = candidate["content"]["parts"][0]["text"].strip()
                        
                        match = re.search(r'\d+', response_text)
                        if match:
                            choice_num = int(match.group())
                            if 1 <= choice_num <= len(candidate_urls):
                                log_msg = f"[✅] {key_id}: Đánh giá ảnh thành công"
                                self.fallback_log.append(log_msg)
                                return candidate_urls[choice_num - 1]
                
                # Success but no valid choice
                return candidate_urls[0]
            
            except requests.exceptions.Timeout:
                status["failure_count"] += 1
                last_error = "Timeout"
                logger.warning(f"[⏱️ TIMEOUT] {key_id} bị timeout, thử key tiếp theo...")
                continue
            except requests.exceptions.ConnectionError:
                status["failure_count"] += 1
                last_error = "Connection failed"
                logger.warning(f"[🔌 CONNECTION] {key_id} mất kết nối, thử key tiếp theo...")
                continue
            except Exception as e:
                status["failure_count"] += 1
                last_error = str(e)
                logger.warning(f"[❌ ERROR] {key_id} lỗi: {e}, thử key tiếp theo...")
                continue
        
        # Tất cả keys đều failed
        error_msg = f"Tất cả {len(self.api_keys)} Gemini API keys đều thất bại: {last_error}"
        raise AIProviderError(error_msg)
    
    def get_status_report(self) -> str:
        """Lấy báo cáo trạng thái của tất cả API keys"""
        report = "📊 Gemini Image Evaluator Status:\n"
        for key_id, status in self.api_key_status.items():
            blocked_status = "🔴 BLOCKED" if status["blocked"] else "🟢 ACTIVE"
            report += f"{key_id}: {blocked_status} (Failures: {status['failure_count']})\n"
        return report

