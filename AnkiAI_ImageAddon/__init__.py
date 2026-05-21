"""
AnkiAI - Tự động thêm ảnh bằng AI
Main entry point cho add-on
"""

from aqt import mw
from aqt.browser import Browser
from aqt.qt import QMessageBox, QDialog
import sys
import os
import logging
import re
import time
import threading
import traceback

# Configure logging - write to file for debugging
_log_file = os.path.join(os.path.expanduser("~"), "Desktop", "AnkiAI-ImageAddon", "ankiai_debug.log")
_file_handler = logging.FileHandler(_log_file, mode="w", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.DEBUG)
_root_logger.addHandler(_file_handler)
logger = logging.getLogger(__name__)

# Import modules
from .modules.config import get_config_manager
from .modules.ui import BrowserMenuManager, FieldSelectionDialog, ConfigDialog, ProgressDialog, get_note_data
from .modules.api_handler import AIImageProvider, APIError
from .modules.image_handler import ImageHandler, ImageError
from .modules.bg_handler import BackgroundProcessor, ProcessingTask
from .modules.features import FeatureDatabase, AdvancedFeatures


# Global instances
browser_menu_manager = None
image_handler = None
bg_processor = None
config_manager = None
feature_db = None
advanced_features = None


class AddImageTask(ProcessingTask):
    """Task để tự động thêm ảnh vào từng thẻ - ✨ OPTIMIZED"""
    
    # ✨ OPTIMIZE: Pre-compile regex at class level (not per-note)
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
    
    def __init__(self, ai_provider, image_handler_obj, vocab_field: str,
                 definition_field: str, examples_field: str, image_field: str):
        super().__init__("Add Images with AI")
        self.ai_provider = ai_provider
        self.image_handler = image_handler_obj
        self.vocab_field = vocab_field
        self.definition_field = definition_field
        self.examples_field = examples_field  # ✨ NEW: Examples field
        self.image_field = image_field
    
    def process_note(self, note) -> tuple:
        """
        Xử lý một note: Lấy từ vựng -> Gọi AI -> Tải ảnh -> Chèn vào note
        
        Args:
            note: Anki Note object
        
        Returns:
            Tuple (success, message)
        """
        try:
            # 1. Lấy từ vựng, định nghĩa và ví dụ từ note
            vocabulary = note[self.vocab_field].strip()
            definition = note[self.definition_field].strip() if self.definition_field in note else ""
            examples = note[self.examples_field].strip() if self.examples_field and self.examples_field in note else ""  # ✨ NEW
            
            if not vocabulary:
                logger.warning(f"📌 Vocabulary field is empty")
                return False, "Từ vựng trống"
            
            # ✨ OPTIMIZE: Use pre-compiled regex (not recompiled per note)
            vocabulary = AddImageTask.HTML_TAG_PATTERN.sub("", vocabulary)
            definition = AddImageTask.HTML_TAG_PATTERN.sub("", definition)
            examples = AddImageTask.HTML_TAG_PATTERN.sub("", examples)  # ✨ NEW
            
            logger.info(f"📌 Processing note: vocab='{vocabulary}'")
            
            # 2. Kiểm tra xem đã có ảnh không
            current_image = note[self.image_field] if self.image_field in note else ""
            if current_image and "<img" in current_image:
                logger.info(f"📌 Image already exists for '{vocabulary}'")
                return False, "Đã có ảnh"
            
            # 3. Gọi AI để lấy URL ảnh (cùng với examples)
            logger.info(f"📌 Calling AI for '{vocabulary}'...")
            image_url = self.ai_provider.get_image_url(vocabulary, definition, examples)
            
            if not image_url:
                logger.warning(f"📌 AI returned no image URL for '{vocabulary}'")
                return False, "AI không tìm được ảnh"
            
            logger.info(f"📌 Got image URL: {image_url[:80]}...")
            
            # 4. Xử lý ảnh
            logger.debug(f"📌 Processing image for '{vocabulary}'...")
            success, message = self.image_handler.process_image(
                image_url, note, vocabulary, self.image_field
            )
            
            logger.info(f"📌 Image processing result: success={success}, msg={message}")
            
            if success:
                # ✨ NOTE: Do NOT call note.flush() here!
                # The background processor will call col.update_note() + col.save()
                # Using both flush() and update_note() causes conflicts in Anki 25.x
                logger.info(f"✅ Note modified, will be saved by background processor: {vocabulary}")
                return True, f"Thêm ảnh thành công: {vocabulary}"
            else:
                logger.warning(f"📌 Image processing failed: {message}")
                return False, message
        
        except APIError as e:
            return False, f"API Error: {str(e)}"
        except ImageError as e:
            return False, f"Image Error: {str(e)}"
        except Exception as e:
            return False, f"Lỗi không xác định: {str(e)}"


def on_browser_menu_add_images(browser: Browser):
    """
    Callback khi người dùng chọn "Tự động thêm ảnh"
    
    Quy trình:
    1. Lấy danh sách thẻ được chọn
    2. Hiển thị dialog chọn fields
    3. Hiển thị dialog cấu hình API
    4. Chạy xử lý background
    """
    
    # Bước 1: Lấy danh sách thẻ được chọn
    note_ids = browser_menu_manager.get_selected_note_ids(browser)
    
    if not note_ids:
        browser_menu_manager.show_warning(
            "Cảnh báo",
            "Vui lòng chọn ít nhất 1 thẻ"
        )
        return
    
    logger.info(f"[ADDON] Selected {len(note_ids)} notes")
    
    # ✨ OPTIMIZE: Single reload + cache all values (not multiple reloads)
    config_manager.reload()
    
    # Bước 2: Kiểm tra API key (Groq hoặc Gemini) - reuse cached values
    has_groq = bool(config_manager.get("groq_api_key"))
    has_gemini = bool(config_manager.get("gemini_api_key"))
    
    if not has_groq and not has_gemini:
        reply = browser_menu_manager.show_question(
            "Cấu hình",
            "Chưa có AI provider nào được cấu hình (Groq hoặc Gemini).\nBạn muốn cấu hình ngay bây giờ?"
        )
        
        if reply:
            config_dialog = ConfigDialog(browser, existing_config=config_manager.get_all())
            if config_dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    config = config_dialog.get_config()
                    config_manager.set("groq_api_key", config.get("groq_api_key", ""))
                    config_manager.set("gemini_api_key", config.get("gemini_api_key", ""))
                    config_manager.set("gemini_backup_api_key", config.get("gemini_backup_api_key", ""))  # v4.0
                    config_manager.set("gemini_keyword_api_key_backup", config.get("gemini_keyword_api_key_backup", ""))  # ✨ NEW v4.2
                    # 🆕 v4.4: Set 7 Gemini Image Evaluator API keys
                    for i in range(1, 8):
                        config_manager.set(f"gemini_eval_api_key_{i}", config.get(f"gemini_eval_api_key_{i}", ""))
                    config_manager.set("enable_ai_evaluation", config.get("enable_ai_evaluation", True))  # 🆕 v4.4
                    config_manager.set("unsplash_api_key", config.get("unsplash_api_key", ""))
                    config_manager.set("pixabay_api_key", config.get("pixabay_api_key", ""))
                    config_manager.set("pexels_api_key", config.get("pexels_api_key", ""))
                    config_manager.set("google_api_key", config.get("google_api_key", ""))  # v4.0
                    config_manager.set("google_cx", config.get("google_cx", ""))  # v4.0
                    config_manager.set("flickr_api_key", config.get("flickr_api_key", ""))
                    config_manager.set("europeana_api_key", config.get("europeana_api_key", ""))
                    config_manager.set("noun_project_api_key", config.get("noun_project_api_key", ""))
                    config_manager.set("noun_project_api_secret", config.get("noun_project_api_secret", ""))
                    config_manager.set("openverse_api_token", config.get("openverse_api_token", ""))
                    config_manager.set("enable_ai_provider_routing", config.get("enable_ai_provider_routing", True))
                    config_manager.set("enable_rate_limit_protection", config.get("enable_rate_limit_protection", True))
                except ValueError as e:
                    browser_menu_manager.show_error("Lỗi cấu hình", str(e))
                    return
            else:
                return
        else:
            return
    
    # Bước 3: Lấy note đầu tiên để xác định fields
    try:
        first_note = mw.col.get_note(note_ids[0])
        available_fields = list(first_note.keys())
        logger.info(f"Available fields: {available_fields}")
    except Exception as e:
        logger.error(f"Error getting first note: {str(e)}")
        browser_menu_manager.show_error("Lỗi", f"Không thể lấy note đầu tiên: {str(e)}")
        return
    
    # Bước 4: Hiển thị dialog chọn fields (luôn hiển thị để user có thể chọn)
    try:
        vocab_field = config_manager.get("vocabulary_field", "Mặt trước")
        definition_field = config_manager.get("definition_field", "Định nghĩa")
        image_field = config_manager.get("image_field", "Ảnh")
        examples_field = config_manager.get("examples_field", "Ví dụ")  # ✨ Initialize from config
        
        logger.info(f"Creating field selection dialog for model: {first_note.note_type()['name']}")
        
        # 🔧 FIX: Luôn hiển thị dialog chọn field
        field_dialog = FieldSelectionDialog(
            first_note.note_type()["name"],
            available_fields,
            browser
        )
        
        logger.info("Showing field selection dialog...")
        if field_dialog.exec() == QDialog.DialogCode.Accepted:
            vocab_field = field_dialog.selected_vocab_field
            definition_field = field_dialog.selected_definition_field
            examples_field = field_dialog.selected_examples_field  # ✨ NEW
            image_field = field_dialog.selected_image_field
            
            logger.info(f"Fields selected: vocab={vocab_field}, def={definition_field}, ex={examples_field}, img={image_field}")
            
            # Lưu vào config
            config_manager.set("vocabulary_field", vocab_field)
            config_manager.set("definition_field", definition_field)
            config_manager.set("examples_field", examples_field)  # ✨ NEW
            config_manager.set("image_field", image_field)
        else:
            logger.info("Field selection dialog cancelled")
            return
    except Exception as e:
        logger.error(f"Error in field selection dialog: {str(e)}")
        browser_menu_manager.show_error("Lỗi", f"Lỗi khi chọn fields: {str(e)}")
        return
    
    # Bước 5: Chuẩn bị AI provider với tất cả providers (v4.2 - multi-key + 15+ providers)
    try:
        # ✨ OPTIMIZE: Use already-reloaded config, don't reload again
        
        # ✨ AI Providers (v4.2 - multi-key for Gemini)
        gemini_key = config_manager.get("gemini_api_key", "")
        gemini_backup_key = config_manager.get("gemini_backup_api_key", "")  # v4.0
        gemini_keyword_backup = config_manager.get("gemini_keyword_api_key_backup", "")  # ✨ NEW v4.2
        groq_key = config_manager.get("groq_api_key", "")
        use_ollama = config_manager.get("use_ollama", False)
        ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
        
        # 🆕 v4.4: Read 7 Gemini Image Evaluator API keys
        gemini_eval_api_key_1 = config_manager.get("gemini_eval_api_key_1", "")
        gemini_eval_api_key_2 = config_manager.get("gemini_eval_api_key_2", "")
        gemini_eval_api_key_3 = config_manager.get("gemini_eval_api_key_3", "")
        gemini_eval_api_key_4 = config_manager.get("gemini_eval_api_key_4", "")
        gemini_eval_api_key_5 = config_manager.get("gemini_eval_api_key_5", "")
        gemini_eval_api_key_6 = config_manager.get("gemini_eval_api_key_6", "")
        gemini_eval_api_key_7 = config_manager.get("gemini_eval_api_key_7", "")
        
        # v5.0: full provider config for registry
        provider_config = config_manager.get_all()
        enable_ai_evaluation = config_manager.get("enable_ai_evaluation", True)
        enable_smart_selection = config_manager.get("enable_smart_selection", True)
        enable_ai_provider_routing = config_manager.get(
            "enable_ai_provider_routing", True
        )
        max_concurrent_providers = config_manager.get("max_concurrent_providers", 10)
        enable_adaptive_delay = config_manager.get("enable_adaptive_delay", True)
        base_delay_ms = config_manager.get("base_delay_ms", 100)
        max_delay_ms = config_manager.get("max_delay_ms", 2000)

        ai_provider = AIImageProvider(
            gemini_key=gemini_key,
            gemini_backup_key=gemini_backup_key,
            gemini_keyword_backup=gemini_keyword_backup,
            gemini_eval_api_key_1=gemini_eval_api_key_1,
            gemini_eval_api_key_2=gemini_eval_api_key_2,
            gemini_eval_api_key_3=gemini_eval_api_key_3,
            gemini_eval_api_key_4=gemini_eval_api_key_4,
            gemini_eval_api_key_5=gemini_eval_api_key_5,
            gemini_eval_api_key_6=gemini_eval_api_key_6,
            gemini_eval_api_key_7=gemini_eval_api_key_7,
            groq_key=groq_key,
            use_ollama=use_ollama,
            ollama_url=ollama_url,
            provider_config=provider_config,
            enable_smart_selection=enable_smart_selection,
            enable_ai_evaluation=enable_ai_evaluation,
            enable_ai_provider_routing=enable_ai_provider_routing,
            max_concurrent_providers=max_concurrent_providers,
            enable_adaptive_delay=enable_adaptive_delay,
            base_delay_ms=base_delay_ms,
            max_delay_ms=max_delay_ms,
        )
    except APIError as e:
        browser_menu_manager.show_error("Lỗi API", str(e))
        return
    
    # Bước 6: Hiển thị confirm dialog
    confirm_msg = f"""Bạn sắp thêm ảnh AI cho {len(note_ids)} thẻ.

Chế độ: Search (dùng Gemini/Groq/Ollama + Image Provider)
Field từ vựng: {vocab_field}
Field ảnh: {image_field}

Tiếp tục?"""
    
    if not browser_menu_manager.show_question("Xác nhận", confirm_msg):
        return
    
    # Bước 7: Tạo Progress Dialog
    progress_dialog = ProgressDialog(len(note_ids), browser)
    progress_dialog.show()
    
    # Bước 8: Chạy background processing
    task = AddImageTask(
        ai_provider,
        image_handler,
        vocab_field,
        definition_field,
        examples_field,  # ✨ NEW: Examples field
        image_field
    )
    
    successful_count = 0
    failed_count = 0
    
    # ✨ OPTIMIZE: Batch UI updates (reduce main thread thrashing)
    last_ui_update = [0]  # Track last update time
    update_interval_ms = 500  # Update UI every 500ms
    
    def on_progress(current, total, message):
        logger.debug(f"[PROGRESS] {current}/{total}: {message}")
        
        # Only update UI every update_interval_ms or on completion
        now = time.time() * 1000
        should_update = (now - last_ui_update[0] > update_interval_ms) or (current == total)
        
        if should_update:
            last_ui_update[0] = now
            # Cập nhật progress dialog từ main thread
            def _update_ui():
                if not progress_dialog.is_cancelled:
                    # Parse message để lấy status và detail
                    parts = message.split(" | ")
                    status_msg = parts[0] if len(parts) > 0 else message
                    detail_msg = parts[1] if len(parts) > 1 else ""
                    
                    progress_dialog.update_progress(current, total, status_msg, detail_msg)
                    progress_dialog.update_stats(successful_count, failed_count)
            
            mw.taskman.run_on_main(_update_ui)
    
    def on_success(result):
        logger.info(f"[SUCCESS] Background processing completed")
        results = result.get("results", [])
        errors = result.get("errors", [])
        
        # Count successful operations (results is list of tuples: (success, message))
        successful = [r for r in results if isinstance(r, tuple) and r[0]]
        # Count failures: both exception errors AND notes that returned (False, message)
        failed_results = [r for r in results if isinstance(r, tuple) and not r[0]]
        failed_errors = [e for e in errors if e]
        all_failures = [r[1] for r in failed_results] + failed_errors
        
        nonlocal successful_count, failed_count
        successful_count = len(successful)
        failed_count = len(all_failures)
        
        # Cập nhật progress dialog hoàn thành
        def _finish_ui():
            progress_dialog.finish(successful_count, failed_count)
            
            # Hiển thị summary
            summary = f"""✅ Hoàn thành!

Thành công: {successful_count}
Thất bại: {failed_count}"""
            
            if all_failures:
                summary += "\n\nLỗi (5 lỗi đầu):"
                for error in all_failures[:5]:
                    summary += f"\n- {error}"
            
            progress_dialog.detail_label.setText(summary)
        
        mw.taskman.run_on_main(_finish_ui)
        
        # Refresh browser on main thread after a short delay
        def refresh_after_delay():
            time.sleep(1)
            try:
                mw.taskman.run_on_main(browser.search)
            except Exception as e:
                logger.debug(f"Browser refresh failed (window may be closed): {e}")
        
        refresh_thread = threading.Thread(target=refresh_after_delay, daemon=True)
        refresh_thread.start()
    
    def on_error(error_msg):
        logger.error(f"[ERROR] {error_msg}")
        def _error_ui():
            progress_dialog.reject()
            browser_menu_manager.show_error("Lỗi", error_msg)
        mw.taskman.run_on_main(_error_ui)
    
    # Xử lý từng note ở background
    def process_func(note):
        success, message = task.process_note(note)
        return success, message
    
    bg_processor.process_cards_in_background(
        note_ids,
        process_func,
        on_progress=on_progress,
        on_success=on_success,
        on_error=on_error,
        title=f"AnkiAI - Đang thêm ảnh ({len(note_ids)} thẻ)"
    )


def open_config_dialog():
    """Mở dialog cấu hình từ Addon Manager"""
    global config_manager
    
    # Luôn tạo mới config_manager để đảm bảo lấy config mới nhất từ Anki
    config_manager = get_config_manager()
    
    # Force reload config từ Anki
    fresh_config = mw.addonManager.getConfig(config_manager.ADDON_MODULE)
    if fresh_config:
        config_manager.config = fresh_config
        logger.info(f"[open_config_dialog] Loaded fresh config from Anki")
    else:
        logger.info(f"[open_config_dialog] No config found, using defaults")
    
    logger.debug(f"[open_config_dialog] Current config: {config_manager.get_all()}")
    
    config_dialog = ConfigDialog(mw, existing_config=config_manager.get_all())
    if config_dialog.exec() == QDialog.DialogCode.Accepted:
        try:
            config = config_dialog.get_config()
            logger.debug(f"[open_config_dialog] Saving config")
            # Lưu tất cả config values (v4.2)
            config_manager.set("groq_api_key", config.get("groq_api_key", ""))
            config_manager.set("gemini_api_key", config.get("gemini_api_key", ""))
            config_manager.set("gemini_backup_api_key", config.get("gemini_backup_api_key", ""))  # v4.0
            config_manager.set("gemini_keyword_api_key_backup", config.get("gemini_keyword_api_key_backup", ""))  # ✨ NEW v4.2
            # 🆕 v4.4: Set 7 Gemini Image Evaluator API keys
            for i in range(1, 8):
                config_manager.set(f"gemini_eval_api_key_{i}", config.get(f"gemini_eval_api_key_{i}", ""))
            config_manager.set("enable_ai_evaluation", config.get("enable_ai_evaluation", True))  # 🆕 v4.4
            config_manager.set("use_ollama", config.get("use_ollama", False))
            config_manager.set("ollama_url", config.get("ollama_url", "http://localhost:11434"))
            config_manager.set("unsplash_api_key", config.get("unsplash_api_key", ""))
            config_manager.set("pixabay_api_key", config.get("pixabay_api_key", ""))
            config_manager.set("pexels_api_key", config.get("pexels_api_key", ""))
            config_manager.set("wallhaven_api_key", config.get("wallhaven_api_key", ""))
            config_manager.set("google_api_key", config.get("google_api_key", ""))
            config_manager.set("google_cx", config.get("google_cx", ""))
            config_manager.set("flickr_api_key", config.get("flickr_api_key", ""))  # ✨ NEW v4.2
            config_manager.set("europeana_api_key", config.get("europeana_api_key", ""))
            config_manager.set("noun_project_api_key", config.get("noun_project_api_key", ""))
            config_manager.set("noun_project_api_secret", config.get("noun_project_api_secret", ""))
            config_manager.set("openverse_api_token", config.get("openverse_api_token", ""))
            config_manager.set("enable_ai_provider_routing", config.get("enable_ai_provider_routing", True))
            config_manager.set("enable_smart_selection", config.get("enable_smart_selection", True))
            config_manager.set("enable_rate_limit_protection", config.get("enable_rate_limit_protection", True))
            config_manager.set("max_concurrent_providers", config.get("max_concurrent_providers", 10))
            config_manager.set("image_generation_mode", config.get("image_generation_mode", "search"))
            
            # Force save config
            config_manager.save_config()
            
            logger.info(f"[open_config_dialog] Config saved successfully")
            QMessageBox.information(mw, "AnkiAI", "Đã lưu cấu hình thành công! ✓")
        except ValueError as e:
            QMessageBox.warning(mw, "Lỗi cấu hình", str(e))


def on_config_changed(new_config):
    """Callback khi config thay đổi từ Anki JSON editor"""
    global config_manager
    if config_manager is not None:
        config_manager.config = new_config
        logger.info("[ADDON] Config updated from Anki editor")


def setup_addon():
    """Setup add-on khi Anki khởi động"""
    global browser_menu_manager, image_handler, bg_processor, config_manager, feature_db, advanced_features
    
    logger.info("[ADDON] Initializing AnkiAI...")
    
    try:
        # Khởi tạo các components
        config_manager = get_config_manager()
        browser_menu_manager = BrowserMenuManager()
        image_handler = ImageHandler(mw)
        bg_processor = BackgroundProcessor()
        
        # 🆕 v4.5: Initialize feature database and advanced features
        if mw.col:
            feature_db = FeatureDatabase(os.path.dirname(mw.col.path))
            advanced_features = AdvancedFeatures(feature_db)
            logger.info("[ADDON] Advanced features database initialized")
        else:
            logger.warning("[ADDON] Collection not ready, skipping feature database init")
        
        # Hook vào Browser
        from aqt import gui_hooks
        
        def setup_browser_menus(browser):
            browser_menu_manager.setup_browser_menu(
                browser,
                on_browser_menu_add_images
            )
        
        gui_hooks.browser_menus_did_init.append(setup_browser_menus)
        
        logger.info("[ADDON] AnkiAI initialized successfully!")
    
    except Exception as e:
        logger.error(f"[ADDON] Error during initialization: {e}")
        traceback.print_exc()


def cleanup_addon():
    """Cleanup resources when addon is disabled or profile closes"""
    global image_handler, bg_processor, config_manager, browser_menu_manager, feature_db, advanced_features
    
    try:
        # 🚀 v4.5: Close all image provider sessions (global session manager)
        try:
            from .modules.image_providers import _ImageProviderSessionManager
            _ImageProviderSessionManager.close_all()
            logger.info("[ADDON] Image provider sessions closed (20-30% resource savings)")
        except Exception as e:
            logger.error(f"[ADDON] Warning: Could not close image provider sessions: {e}")
        
        # Close HTTP session if image handler exists
        if image_handler and hasattr(image_handler, 'session'):
            try:
                image_handler.session.close()
            except Exception:
                logger.debug("[ADDON] Could not close HTTP session")
            logger.info("[ADDON] HTTP session closed")
        
        # Stop background processor if running
        if bg_processor and hasattr(bg_processor, 'stop'):
            bg_processor.stop()
            logger.info("[ADDON] Background processor stopped")
        
        # Close feature database
        if feature_db and hasattr(feature_db, 'db_path'):
            logger.info("[ADDON] Feature database closed")
        
        # Clear references
        image_handler = None
        bg_processor = None
        config_manager = None
        browser_menu_manager = None
        feature_db = None
        advanced_features = None
        
        logger.info("[ADDON] Cleanup completed")
    
    except Exception as e:
        logger.error(f"[ADDON] Cleanup error: {e}")


# === Đăng ký config action NGAY khi addon được load (trước khi mở profile) ===
_addon_dir = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
mw.addonManager.setConfigAction(_addon_dir, open_config_dialog)
mw.addonManager.setConfigUpdatedAction(_addon_dir, on_config_changed)

# Hook vào Anki startup
from aqt import gui_hooks
gui_hooks.profile_did_open.append(setup_addon)
gui_hooks.profile_will_close.append(cleanup_addon)
