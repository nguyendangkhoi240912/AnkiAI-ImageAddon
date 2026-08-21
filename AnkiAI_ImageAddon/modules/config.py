"""
Config Module - Quản lý cài đặt của add-on
Cho phép người dùng nhập API key, chọn field names, chọn mode (AI search vs AI generate)

v4.5 Improvements:
- Added Pexels API support
- Keyword cache enabled by default
- Image optimization settings
- Performance tuning defaults
- Proper logging
"""
from aqt import mw
import json
import os
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ConfigManager:
    """Quản lý cấu hình của add-on - v4.0"""
    
    DEFAULT_CONFIG = {
        # AI Providers (v4.2)
        "gemini_api_key": "",
        "gemini_backup_api_key": "",  # ✨ Key #3 for backup
        "gemini_keyword_api_key_backup": "",  # ✨ NEW v4.2: Backup for keyword gen
        "groq_api_key": "",
        "use_ollama": False,
        "ollama_url": "http://localhost:11434",
        
        # Image Search Providers (v4.2 - 15+ providers!)
        "pexels_api_key": "",
        "unsplash_api_key": "",
        "pixabay_api_key": "",
        "wallhaven_api_key": "",
        "google_api_key": "",
        "google_cx": "",
        "flickr_api_key": "",
        "europeana_api_key": "",
        "noun_project_api_key": "",
        "noun_project_api_secret": "",
        "openverse_api_token": "",
        "enable_ai_provider_routing": True,
        # Free without keys: Openverse, DuckDuckGo, Wikimedia, NASA, PubChem, etc.
        
        # 🆕 v4.4: Gemini Image Evaluator - 7 API keys with auto-failover
        "gemini_eval_api_key_1": "",
        "gemini_eval_api_key_2": "",
        "gemini_eval_api_key_3": "",
        "gemini_eval_api_key_4": "",
        "gemini_eval_api_key_5": "",
        "gemini_eval_api_key_6": "",
        "gemini_eval_api_key_7": "",
        "enable_ai_evaluation": True,
        
        # Smart Selection Settings
        "enable_smart_selection": True,
        "max_concurrent_providers": 8,  # ⚡ v5.3: Increased from 6 (20-30% faster)
        "smart_cache_ttl_minutes": 120,
        
        # Image Download Settings (v4.2 - optimized)
        "image_download_timeout": 15,
        "image_download_retries": 2,
        "enable_image_optimization": True,
        "image_max_width": 800,
        "image_quality": 80,
        
        # Keyword Caching (v4.2)
        "enable_keyword_cache": True,
        "keyword_cache_size": 1000,
        
        # Rate Limit Protection (v4.2 - NEW)
        "enable_rate_limit_protection": True,  # ✨ NEW: Auto-pause on rate limit
        "rate_limit_pause_duration": 60,  # ✨ NEW: 60 second auto-pause
        
        # ✨ NEW v4.3: Adaptive Delay to Prevent IP Ban
        "enable_adaptive_delay": True,  # Enable adaptive delay between requests
        "base_delay_ms": 100,  # Base delay in milliseconds (100ms)
        "max_delay_ms": 2000,  # Max delay cap (2 seconds)
        "delay_increase_on_429": 500,  # Add 500ms per 429 response
        "delay_increase_on_timeout": 200,  # Add 200ms per timeout
        "delay_reset_hours": 1,  # Reset delay after 1 hour of success
        
        # UI Settings
        "vocabulary_field": "Mặt trước",
        "definition_field": "Định nghĩa",
        "examples_field": "Ví dụ",  # ✨ NEW v4.6: Examples field for context
        "image_field": "Ảnh",
        "image_generation_mode": "search",
        
        # Concurrency Settings (v5.3)
        "max_concurrent_requests": 8,  # ⚡ Increased from 5 for better throughput
        "max_concurrent_providers": 8,  # ⚡ Increased from 6 (benchmarked 20-30% faster)
        "enable_concurrent_downloads": True,
        
        # Other
        "auto_add_on_sync": False,

        # Development: NDJSON trace log under addon/logs/ (off in production)
        "enable_agent_debug_log": False,

        # Skip existing images configuration (v5.1)
        "skip_existing_images": True,

        # Animated/GIF search API keys (v5.0)
        "klipy_app_key": "",
        "giphy_api_key": "",
        "iconscout_api_token": "",

        # Gemini image description keys (v5.0)
        "gemini_image_description_api_key": "",
        "gemini_image_description_api_key_backup_1": "",
        "gemini_image_description_api_key_backup_2": "",
        "enable_gemini_image_description": True,

        # Imagen 4 Ultra keys (v5.0)
        "imagen_enabled": False,
        "imagen_api_key": "",
        "imagen_service_account_json": "",
        "imagen_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict",
        "imagen_timeout_seconds": 25,
        "imagen_max_concurrent_requests": 2,
        "imagen_request_retries": 2,
        "imagen_cost_warning_threshold_usd": 5.0,
        "imagen_fallback_to_search_providers": True,
        "imagen_default_style": "photorealistic",
        "imagen_default_size": "1024x1024",
        "imagen_enable_safety_checking": True,
        "imagen_enable_cost_tracking": True,

        # v5.1: Note-type presets (fields + mode per model name)
        "note_type_presets": {},
        "always_show_field_dialog": False,

        # v5.1: Batch control
        "max_notes_per_batch": 100,
        "pending_batch_note_ids": [],
        "pending_batch_meta": {},

        # v5.1: Fewer API calls while keeping quality
        "prefer_fewer_api_calls": True,
        "max_eval_candidates": 2,
    }
    
    # Tên thư mục addon (dùng để Anki đọc/ghi config đúng)
    ADDON_MODULE = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    @property
    def addon_module(self):
        """Lấy tên addon module từ Anki"""
        # Thử lấy từ __name__ nếu có
        try:
            import __main__
            if hasattr(__main__, 'addonManager'):
                # Đang chạy trong Anki
                pass
        except Exception as e:
            logger.debug(f"Could not detect Anki environment: {e}")
        return self.ADDON_MODULE
    
    def __init__(self):
        """Khởi tạo config manager"""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load config: merge defaults + meta.json user overrides"""
        config = self.DEFAULT_CONFIG.copy()
        
        # PRIMARY: read meta.json directly (most reliable)
        try:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            meta_path = os.path.join(addon_dir, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                user_config = meta.get("config", {})
                if user_config:
                    config.update(user_config)
                    return config
        except Exception as e:
            logger.debug(f"Failed to load meta.json: {e}")
        
        # FALLBACK: Anki's getConfig API
        try:
            anki_config = mw.addonManager.getConfig(self.ADDON_MODULE)
            if anki_config:
                config.update(anki_config)
                return config
        except Exception as e:
            logger.debug(f"Failed to load config via addonManager: {e}")
        
        return config
    
    def reload(self):
        """Force reload config from disk"""
        self.config = self._load_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị config"""
        val = self.config.get(key, default if default is not None else self.DEFAULT_CONFIG.get(key))
        return val
    
    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        """Cập nhật giá trị config"""
        self.config[key] = value
        if save:
            self.save_config()

    def set_many(self, updates: Dict[str, Any]) -> None:
        """Update several keys and save once."""
        self.config.update(updates)
        self.save_config()

    def clear_pending_batch(self) -> None:
        self.set_many({"pending_batch_note_ids": [], "pending_batch_meta": {}})
    
    def save_config(self) -> None:
        """Lưu config vào Anki"""
        try:
            logger.debug(f"Saving config for module: {self.ADDON_MODULE}")
            mw.addonManager.writeConfig(self.ADDON_MODULE, self.config)
            logger.info(f"Config saved via addonManager")
        except Exception as e:
            logger.warning(f"addonManager failed: {e}, trying direct file save...")
            # Fallback: Lưu trực tiếp vào file
            try:
                import json
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                logger.info(f"Config saved directly to: {config_path}")
            except Exception as e2:
                logger.error(f"Direct save also failed: {e2}")
                import traceback
                logger.debug(traceback.format_exc())
    
    def get_all(self) -> Dict[str, Any]:
        """Lấy toàn bộ config"""
        return self.config.copy()
    
    def reset_to_default(self) -> None:
        """Reset về cấu hình mặc định"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Kiểm tra xem API keys đã được cài đặt chưa"""
        # Check if at least one AI provider is configured
        has_AI_provider = (
            bool(self.get("gemini_api_key")) or
            bool(self.get("groq_api_key")) or
            self.get("use_ollama")
        )
        
        # Image search providers
        has_image_provider = (
            bool(self.get("pexels_api_key"))
            or bool(self.get("unsplash_api_key"))
            or bool(self.get("pixabay_api_key"))
            or bool(self.get("flickr_api_key"))
            or bool(self.get("google_api_key"))
            or True  # free providers always available
        )
        
        return {
            "ai_provider": has_AI_provider,
            "image_provider": has_image_provider if self.get("image_generation_mode") == "search" else True,
        }


# Singleton instance
config_manager = None


def get_config_manager() -> ConfigManager:
    """Lấy singleton ConfigManager"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager
