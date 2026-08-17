"""
Imagen 4 Ultra Generate Integration - v1.0
Image generation for flashcards with Gemini-guided image descriptions
"""

import base64
import logging
import re
import requests
import json
import time
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class ImageProviderError(Exception):
    """Exception cho Imagen provider"""
    pass


def resolve_imagen_predict_url(endpoint: str = "") -> str:
    """Map legacy generateContent URLs to Imagen predict endpoint."""
    default_model = "imagen-4.0-ultra-generate-001"
    if not endpoint or not str(endpoint).strip():
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{default_model}:predict"
        )
    endpoint = str(endpoint).strip()
    if ":predict" in endpoint:
        return endpoint
    match = re.search(r"/models/([^/:]+)", endpoint)
    model_id = match.group(1) if match else default_model
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:predict"
    )


class GeminiImageDescriber:
    """
    Dùng 3 Gemini APIs (1 primary + 2 backup) để tạo image description guide từ:
    - vocabulary (từ vựng)
    - definition (định nghĩa)
    - examples (ví dụ)
    
    Đầu ra: detailed image description cho Imagen để tạo ảnh chính xác hơn
    """
    
    def __init__(self, api_keys: List[str]):
        """
        Khởi tạo GeminiImageDescriber với 3 Gemini API keys
        
        Args:
            api_keys: List [primary_key, backup_key_1, backup_key_2]
        """
        self.api_keys = [k.strip() for k in api_keys if k and k.strip()]
        if not self.api_keys:
            raise ImageProviderError("At least one Gemini API key required for image description")
        
        self.model = "gemini-3.5-flash-lite"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.timeout = 8
        self.cache = {}
        self.lock = threading.Lock()
        
        # Session management
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=5,
            max_retries=Retry(total=2, backoff_factor=0.1)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def _get_cache_key(self, vocabulary: str, definition: str, examples: str) -> str:
        """Tạo cache key từ vocabulary + definition + examples"""
        import hashlib
        key = f"{vocabulary}|{definition}|{examples}".encode('utf-8')
        return hashlib.md5(key).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[str]:
        """Kiểm tra cache"""
        with self.lock:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if datetime.now() < entry['expires']:
                    return entry['description']
                else:
                    del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, description: str, ttl_hours: int = 24):
        """Lưu vào cache"""
        with self.lock:
            self.cache[cache_key] = {
                'description': description,
                'expires': datetime.now() + timedelta(hours=ttl_hours)
            }
    
    def generate_image_description(
        self, 
        vocabulary: str, 
        definition: str, 
        examples: str = ""
    ) -> str:
        """
        Generate detailed image description guide từ vocabulary, definition, examples
        
        Args:
            vocabulary: Từ vựng tiếng Anh
            definition: Định nghĩa chi tiết
            examples: Ví dụ sử dụng (optional)
        
        Returns:
            Image description prompt cho Imagen (chi tiết, chính xác)
        """
        cache_key = self._get_cache_key(vocabulary, definition, examples)
        cached = self._check_cache(cache_key)
        if cached:
            logger.info(f"[Cache] Image description for '{vocabulary}' found")
            return cached
        
        prompt = self._build_prompt(vocabulary, definition, examples)
        
        last_error = None
        for idx, api_key in enumerate(self.api_keys):
            try:
                key_label = "PRIMARY" if idx == 0 else f"BACKUP_{idx}"
                logger.info(f"[Gemini-ImageDescriber] Using {key_label} key for '{vocabulary}'")
                
                response = self.session.post(
                    f"{self.base_url}/{self.model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 150
                        }
                    },
                    timeout=self.timeout
                )
                
                # On resource errors, break immediately — keep gemini-3.5-flash-lite
                # and let the API key rotation handle retries instead of downgrading model
                if response.status_code in (400, 403, 404):
                    error_msg = response.json().get("error", {}).get("message", response.text)
                    logger.warning(
                        f"[Gemini-ImageDescriber] {self.model} returned {response.status_code}: "
                        f"{error_msg} — skipping to next API key"
                    )
                
                if response.status_code != 200:
                    error_msg = response.json().get("error", {}).get("message", response.text)
                    last_error = error_msg
                    logger.warning(f"[{key_label}] Error: {error_msg}")
                    continue
                
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        description = candidate["content"]["parts"][0]["text"].strip()
                        self._set_cache(cache_key, description)
                        logger.info(f"[✓] {key_label} success: Generated image description")
                        return description
                
                last_error = "Empty response"
                continue
            
            except requests.exceptions.Timeout:
                last_error = "Timeout"
                logger.warning(f"[Timeout] Key {idx} timed out")
                continue
            except requests.exceptions.ConnectionError:
                last_error = "Connection failed"
                logger.warning(f"[Connection] Key {idx} connection failed")
                continue
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[Error] Key {idx}: {e}")
                continue
        
        raise ImageProviderError(
            f"All Gemini image description keys failed: {last_error}"
        )
    
    def _build_prompt(self, vocabulary: str, definition: str, examples: str) -> str:
        """Xây dựng prompt cho Gemini để generate image description"""
        examples_section = ""
        if examples and examples.strip():
            examples_section = f"\n\nExamples of usage:\n{examples}"
        
        prompt = f"""You are an expert at creating detailed visual descriptions for AI image generation.

Word: {vocabulary}
Definition: {definition}{examples_section}

Task: Generate a detailed image description (3-4 sentences, visual and concrete) that captures the essence of this word for use with Imagen 4 Ultra.

Requirements:
1. Be VISUAL and CONCRETE - describe what someone would SEE
2. Include specific visual elements, colors, objects, settings
3. For abstract concepts, describe a SCENE or METAPHOR that represents them
4. For verbs, describe ACTION being performed with context
5. For adjectives, show an OBJECT or SCENE that clearly exhibits that quality
6. Make it DETAILED enough for an AI image generator to understand
7. Avoid using the word itself - focus on visual representation

Output ONLY the image description, nothing else."""
        
        return prompt


class ImagenProvider:
    """
    Google Imagen 4 Ultra Generate Integration
    - Tạo ảnh từ detailed prompts
    - Auto-failover giữa API keys
    - Cost tracking & rate limiting
    - Cache & quota management
    """
    
    def __init__(
        self, 
        api_key: str = "", 
        service_account_json: str = "",
        timeout: int = 25,
        max_concurrent: int = 2,
        retries: int = 2,
        enable_safety: bool = True,
        endpoint: str = "",
    ):
        """
        Khởi tạo Imagen Provider
        
        Args:
            api_key: Google Cloud API key hoặc Imagen API key
            service_account_json: Service account JSON (alternative auth)
            timeout: Request timeout (seconds)
            max_concurrent: Max concurrent image generation requests
            retries: Số lần retry
            enable_safety: Enable safety checking
        """
        if not api_key and not service_account_json:
            raise ImageProviderError("Imagen requires API key or service account JSON")
        
        self.api_key = api_key.strip() if api_key else ""
        self.service_account_json = service_account_json
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.retries = retries
        self.enable_safety = enable_safety
        
        self.endpoint = resolve_imagen_predict_url(endpoint)
        match = re.search(r"/models/([^/:]+)", self.endpoint)
        self.model = match.group(1) if match else "imagen-4.0-ultra-generate-001"
        
        # Session management
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=self.max_concurrent,
            pool_maxsize=self.max_concurrent,
            max_retries=Retry(total=retries, backoff_factor=0.3)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Tracking
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_cost_usd = 0.0
        self.lock = threading.Lock()
    
    def is_available(self) -> bool:
        """Kiểm tra Imagen có sẵn sàng"""
        try:
            # Quick health check
            response = self.session.get(
                self.endpoint,
                params={"key": self.api_key},
                timeout=3
            )
            # 400 = key valid nhưng request invalid (expected for GET)
            # 401/403 = auth failed
            return response.status_code in [200, 400]
        except Exception as e:
            logger.warning(f"Imagen availability check failed: {e}")
            return False
    
    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        style: str = "photorealistic"
    ) -> List[bytes]:
        """
        Generate images từ prompt bằng Imagen 4 Ultra
        
        Args:
            prompt: Detailed image description
            width: Image width (supported: 256, 512, 1024, 1536)
            height: Image height (supported: 256, 512, 1024, 1536)
            num_images: Số ảnh tạo (1-4, mặc định 1)
            style: Style preset (photorealistic, illustration, etc.)
        
        Returns:
            List of image bytes
        """
        with self.lock:
            self.request_count += 1
        
        if num_images < 1 or num_images > 4:
            raise ImageProviderError("num_images must be between 1 and 4")
        
        # Validate dimensions
        valid_sizes = [256, 512, 1024, 1536]
        if width not in valid_sizes or height not in valid_sizes:
            width, height = 1024, 1024
            logger.warning(f"Invalid size, using 1024x1024")
        
        # Thêm style guidance vào prompt
        styled_prompt = self._add_style_guidance(prompt, style)
        
        request_body = {
            "instances": [{"prompt": styled_prompt}],
            "parameters": self._build_predict_parameters(width, height, num_images),
        }
        
        last_error = None
        for attempt in range(self.retries):
            try:
                logger.info(
                    f"[Imagen] Generating image via {self.model} "
                    f"(attempt {attempt + 1}/{self.retries})..."
                )
                
                response = self.session.post(
                    self.endpoint,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    json=request_body,
                    timeout=self.timeout
                )
                
                if response.status_code == 429:
                    last_error = "Rate limited"
                    wait_time = min(5 * (attempt + 1), 30)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Try fallback models if we get resource errors
                while response.status_code in (400, 403, 404):
                    if "imagen-4.0-ultra" in self.model:
                        logger.info("Imagen 4 Ultra failed/not supported. Falling back to Imagen 4 Standard...")
                        self.model = "imagen-4.0-generate-001"
                        self.endpoint = resolve_imagen_predict_url(self.model)
                    elif "imagen-4.0-generate" in self.model:
                        logger.info("Imagen 4 Standard failed/not supported. Falling back to Imagen 3...")
                        self.model = "imagen-3.0-generate-002"
                        self.endpoint = resolve_imagen_predict_url(self.model)
                    else:
                        break  # No more fallbacks available
                        
                    logger.info(f"[Imagen] Retrying with model: {self.model}")
                    response = self.session.post(
                        self.endpoint,
                        params={"key": self.api_key},
                        headers={"Content-Type": "application/json"},
                        json=request_body,
                        timeout=self.timeout
                    )

                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except ValueError:
                        error_msg = response.text
                    last_error = f"{response.status_code}: {error_msg}"
                    logger.warning(f"Imagen error: {last_error}")
                    # #region agent log
                    from .debug_log import cursor_session_log

                    cursor_session_log(
                        "imagen_provider.py:generate_image",
                        "predict_http_error",
                        {
                            "status": response.status_code,
                            "model": self.model,
                            "error": str(error_msg)[:240],
                        },
                        "B",
                    )
                    # #endregion
                    continue
                
                result = response.json()
                images = self._extract_images_from_predict_response(result)
                # #region agent log
                from .debug_log import cursor_session_log

                cursor_session_log(
                    "imagen_provider.py:generate_image",
                    "predict_response",
                    {
                        "status": response.status_code,
                        "model": self.model,
                        "image_count": len(images),
                        "prediction_keys": len(result.get("predictions") or []),
                    },
                    "B",
                    run_id="post-fix",
                )
                # #endregion
                if images:
                    with self.lock:
                        self.success_count += 1
                    logger.info(f"[✓] Imagen: Generated {len(images)} image(s)")
                    return images
                
                last_error = "No images in response"
                continue
            
            except requests.exceptions.Timeout:
                last_error = f"Timeout ({self.timeout}s)"
                logger.warning(f"Imagen timeout on attempt {attempt + 1}")
                continue
            except requests.exceptions.ConnectionError:
                last_error = "Connection failed"
                logger.warning(f"Imagen connection error on attempt {attempt + 1}")
                continue
            except Exception as e:
                last_error = str(e)
                logger.error(f"Imagen error on attempt {attempt + 1}: {e}")
                continue
        
        with self.lock:
            self.failure_count += 1
        
        raise ImageProviderError(f"Imagen image generation failed: {last_error}")
    
    def _build_predict_parameters(
        self, width: int, height: int, num_images: int
    ) -> Dict:
        """Map dimensions to Imagen :predict parameters (Gemini API)."""
        if width > height * 1.2:
            aspect_ratio = "16:9" if width / max(height, 1) >= 1.5 else "4:3"
        elif height > width * 1.2:
            aspect_ratio = "9:16" if height / max(width, 1) >= 1.5 else "3:4"
        else:
            aspect_ratio = "1:1"
        image_size = "2K" if max(width, height) >= 1536 else "1K"
        params: Dict = {
            "sampleCount": num_images,
            "aspectRatio": aspect_ratio,
            "imageSize": image_size,
        }
        if self.enable_safety:
            params["personGeneration"] = "allow_adult"
        return params

    def _extract_images_from_predict_response(self, result: dict) -> List[bytes]:
        images: List[bytes] = []
        for pred in result.get("predictions") or []:
            if not isinstance(pred, dict):
                continue
            b64 = pred.get("bytesBase64Encoded") or pred.get("bytesBase64") or ""
            if b64:
                images.append(base64.b64decode(b64))
        if images:
            return images
        for candidate in result.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            image_obj = candidate.get("image") or {}
            b64 = image_obj.get("bytesBase64") or image_obj.get("bytesBase64Encoded") or ""
            if b64:
                images.append(base64.b64decode(b64))
        return images

    def _add_style_guidance(self, prompt: str, style: str) -> str:
        """Thêm style guidance vào prompt"""
        style_guides = {
            "photorealistic": "Create a highly photorealistic, professional photograph.",
            "illustration": "Create a detailed illustration or artwork style image.",
            "cartoon": "Create a cartoon or comic book style illustration.",
            "painting": "Create a painting-style artwork.",
            "3d": "Create a 3D rendered artwork.",
        }
        
        guide = style_guides.get(style, "")
        if guide:
            return f"{prompt}\n\n{guide}"
        return prompt
    
    def get_stats(self) -> Dict:
        """Lấy thống kê sử dụng"""
        with self.lock:
            return {
                "total_requests": self.request_count,
                "successful": self.success_count,
                "failed": self.failure_count,
                "success_rate": (
                    self.success_count / self.request_count * 100 
                    if self.request_count > 0 else 0
                ),
                "total_cost_usd": self.total_cost_usd,
                "avg_cost_per_image": (
                    self.total_cost_usd / self.success_count 
                    if self.success_count > 0 else 0
                )
            }


class ImageGenerationPipeline:
    """
    Pipeline tích hợp: Vocabulary → Gemini Description → Imagen Generation
    """
    
    def __init__(
        self,
        gemini_api_keys: List[str],
        imagen_api_key: str,
        imagen_service_account: str = "",
        enable_fallback_to_search: bool = True,
        imagen_endpoint: str = "",
        imagen_timeout: int = 25,
        imagen_retries: int = 2,
        enable_safety: bool = True,
    ):
        """
        Khởi tạo image generation pipeline
        
        Args:
            gemini_api_keys: [primary, backup1, backup2]
            imagen_api_key: Imagen API key
            imagen_service_account: Service account JSON (optional)
            enable_fallback_to_search: Fallback to search providers nếu Imagen fail
        """
        self.describer = GeminiImageDescriber(gemini_api_keys)
        self.generator = ImagenProvider(
            api_key=imagen_api_key,
            service_account_json=imagen_service_account,
            timeout=imagen_timeout,
            retries=imagen_retries,
            enable_safety=enable_safety,
            endpoint=imagen_endpoint,
        )
        self.enable_fallback = enable_fallback_to_search
        self.generation_log = []
    
    def generate_image_for_vocabulary(
        self,
        vocabulary: str,
        definition: str,
        examples: str = "",
        width: int = 1024,
        height: int = 1024,
        style: str = "photorealistic"
    ) -> Tuple[Optional[List[bytes]], str, Dict]:
        """
        Toàn bộ pipeline: Description → Generate → Tracking
        
        Returns:
            (image_bytes_list, provider_used, metadata)
        """
        metadata = {
            "vocabulary": vocabulary,
            "definition": definition,
            "examples": examples,
            "timestamp": datetime.now().isoformat(),
            "description": None,
            "provider": None,
            "success": False,
            "error": None
        }
        
        try:
            # Step 1: Generate image description using Gemini
            logger.info(f"[Pipeline] Generating image description for '{vocabulary}'...")
            image_description = self.describer.generate_image_description(
                vocabulary, definition, examples
            )
            metadata["description"] = image_description
            
            # Step 2: Generate image using Imagen
            logger.info(f"[Pipeline] Generating image with Imagen...")
            images = self.generator.generate_image(
                prompt=image_description,
                width=width,
                height=height,
                num_images=1,
                style=style
            )
            
            metadata["provider"] = "Imagen"
            metadata["success"] = True
            self.generation_log.append(metadata)
            
            return images, "Imagen", metadata
        
        except ImageProviderError as e:
            metadata["error"] = str(e)
            metadata["provider"] = "Imagen"
            logger.error(f"[Pipeline] Imagen generation failed: {e}")
            
            if self.enable_fallback:
                logger.info(f"[Pipeline] Falling back to search providers...")
                metadata["provider"] = "SearchFallback"
                # TODO: Fallback to SmartImageSelector for search-based images
                return None, "SearchFallback", metadata
            
            self.generation_log.append(metadata)
            return None, "Imagen", metadata
