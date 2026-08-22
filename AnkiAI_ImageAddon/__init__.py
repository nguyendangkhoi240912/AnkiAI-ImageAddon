"""
AnkiAI - Tự động thêm ảnh bằng AI
Main entry point cho add-on
"""

from aqt import mw
from aqt.browser import Browser
from aqt.qt import QMessageBox, QDialog, QTimer
import sys
import os
import logging
from typing import Optional
import re
import time
import traceback
def _setup_file_logging() -> logging.Logger:
    """Log to addon/logs/ankiai.log; skip file handler if directory is not writable."""
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(addon_dir, "logs", "ankiai.log")
    log = logging.getLogger(__name__)
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        if any(
            getattr(h, "baseFilename", None) == log_file
            for h in logging.getLogger().handlers
            if isinstance(h, logging.FileHandler)
        ):
            return log
        handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        )
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)
    except OSError:
        pass
    return log


logger = _setup_file_logging()

# Import modules
from .modules.config import get_config_manager
from .modules.ui import (
    BrowserMenuManager,
    FieldSelectionDialog,
    ConfigDialog,
    ProgressDialog,
    BatchOptionsDialog,
    get_note_data,
)
from .modules.note_presets import get_preset, build_preset
from .modules.api_handler import AIImageProvider, APIError
from .modules.image_handler import ImageHandler, ImageError
from .modules.bg_handler import BackgroundProcessor, ProcessingTask, RetryQueue, IdlePrefetch
from .modules.features import FeatureDatabase, AdvancedFeatures
from .modules.debug_log import configure as configure_debug_log, cursor_session_log
from .modules.http_session_manager import HTTPSessionManager


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

    def _overwrite_existing(self) -> bool:
        return not config_manager.get("skip_existing_images", True)

    def _ensure_image_field(self, note) -> Optional[tuple]:
        if self.image_field in note:
            return None
        available = list(note.keys())
        return False, f"Field '{self.image_field}' không tồn tại. Có: {available}"

    def _apply_generated_bytes(self, note, image_data: bytes, vocabulary: str, overwrite: bool) -> tuple:
        status, detail = self.image_handler.save_and_insert(
            note, image_data, vocabulary, self.image_field, overwrite=overwrite
        )
        if status is True:
            return True, f"Tạo ảnh AI thành công: {detail}"
        if status == "skipped":
            return "skipped", detail
        return False, detail

    @staticmethod
    def _finalize_result(success, message: str, vocabulary: str) -> tuple:
        """Map internal success flag to (True | 'skipped' | False, message)."""
        if success is True:
            return True, message or f"Thêm ảnh thành công: {vocabulary}"
        if success == "skipped":
            return "skipped", message or "Đã có ảnh"
        return False, message or "Thất bại"

    def process_note(self, note) -> tuple:
        """
        Xử lý một note: Lấy từ vựng -> Gọi AI -> Tải ảnh -> Chèn vào note
        
        Args:
            note: Anki Note object
        
        Returns:
            Tuple (success, message) where success is True/False/"skipped"
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
                skip_existing = config_manager.get("skip_existing_images", True)
                if skip_existing:
                    logger.info(f"📌 Image already exists for '{vocabulary}', skipping...")
                    return "skipped", "Đã có ảnh"
                else:
                    logger.info(f"📌 Image already exists for '{vocabulary}', but skip_existing_images is disabled. Overwriting...")
            
            field_error = self._ensure_image_field(note)
            if field_error:
                return field_error

            generation_mode = config_manager.get("image_generation_mode", "search")
            overwrite = self._overwrite_existing()
            logger.info(f"📌 Image generation mode: {generation_mode}")
            
            success = False
            message = ""
            
            if generation_mode == "generate":
                # AI generation mode using Imagen
                logger.info(f"📌 Generating image using AI for '{vocabulary}'...")
                # #region agent log
                cursor_session_log(
                    "__init__.py:AddImageTask.process_note",
                    "generate_mode_start",
                    {
                        "generation_mode": generation_mode,
                        "pipeline_ready": getattr(
                            self.ai_provider, "pipeline", None
                        )
                        is not None,
                        "imagen_enabled": getattr(
                            self.ai_provider, "imagen_enabled", None
                        ),
                        "vocab_preview": (vocabulary or "")[:40],
                    },
                    "A",
                )
                # #endregion
                try:
                    images, provider_name, metadata = self.ai_provider.generate_image_with_imagen(
                        vocabulary=vocabulary,
                        definition=definition,
                        examples=examples
                    )
                    if images and len(images) > 0:
                        success, message = self._apply_generated_bytes(
                            note, images[0], vocabulary, overwrite
                        )
                    else:
                        success = False
                        meta_err = (metadata or {}).get("error") or ""
                        if config_manager.get(
                            "imagen_fallback_to_search_providers", True
                        ):
                            try:
                                image_url = self.ai_provider.get_image_url(
                                    vocabulary, definition, examples
                                )
                                if image_url:
                                    logger.info(
                                        "Imagen empty/failed; using search fallback"
                                    )
                                    success, message = self.image_handler.process_image(
                                        image_url,
                                        note,
                                        vocabulary,
                                        self.image_field,
                                        overwrite=overwrite,
                                    )
                                    if success is True:
                                        message = f"{message} (fallback tìm kiếm)"
                            except Exception as fb_err:
                                logger.warning(
                                    "Search fallback after Imagen failed: %s", fb_err
                                )
                        if not success:
                            if meta_err:
                                message = f"AI không tạo được ảnh: {meta_err[:220]}"
                            else:
                                message = (
                                    "AI không tạo được ảnh "
                                    "(không có dữ liệu trả về)"
                                )
                except Exception as e:
                    logger.error(f"Imagen generation error: {e}", exc_info=True)
                    success = False
                    message = f"Lỗi tạo ảnh AI: {e}"
                    # #region agent log
                    cursor_session_log(
                        "__init__.py:AddImageTask.process_note",
                        "generate_mode_exception",
                        {"error_type": type(e).__name__, "error": str(e)[:300]},
                        "E",
                    )
                    # #endregion
            
            elif generation_mode == "smart":
                # Smart mode: prefer generated, fallback to search
                logger.info(f"📌 Smart image selection for '{vocabulary}'...")
                try:
                    result, source = self.ai_provider.generate_image_smart(
                        vocabulary=vocabulary,
                        definition=definition,
                        examples=examples,
                        prefer_generated=True
                    )
                    
                    if source == "Imagen" and isinstance(result, bytes):
                        success, message = self._apply_generated_bytes(
                            note, result, vocabulary, overwrite
                        )
                        if success is True:
                            message = f"{message} (Smart)"
                    else:
                        # Search-based image URL
                        image_url = result
                        if image_url:
                            logger.info(f"📌 Got search image URL (Smart): {image_url[:80]}...")
                            success, message = self.image_handler.process_image(
                                image_url, note, vocabulary, self.image_field, overwrite=overwrite
                            )
                        else:
                            success = False
                            message = "Smart search không tìm được ảnh"
                except Exception as e:
                    logger.error(f"Smart selection error: {e}", exc_info=True)
                    success = False
                    message = f"Lỗi chọn ảnh thông minh: {e}"
            
            else:
                # Default traditional search mode
                logger.info(f"📌 Searching image for '{vocabulary}'...")
                try:
                    image_url = self.ai_provider.get_image_url(vocabulary, definition, examples)
                    
                    if not image_url:
                        logger.warning(f"📌 AI returned no image URL for '{vocabulary}'")
                        return False, "AI không tìm được ảnh"
                    
                    logger.info(f"📌 Got image URL: {image_url[:80]}...")
                    
                    # 4. Xử lý ảnh (retry fallback URLs if download fails)
                    logger.debug(f"📌 Processing image for '{vocabulary}'...")
                    success, message = self.image_handler.process_image(
                        image_url, note, vocabulary, self.image_field, overwrite=overwrite
                    )

                    # Sequential fallback (same note — avoid parallel races on note/media)
                    if success is not True and success != "skipped" and "Download" in message:
                        fallback_urls = self.ai_provider.get_fallback_image_urls()
                        if fallback_urls:
                            logger.info(
                                f"📌 Primary URL failed, trying {len(fallback_urls)} fallback URLs..."
                            )
                            for url in fallback_urls:
                                try:
                                    result_success, result_msg = self.image_handler.process_image(
                                        url, note, vocabulary, self.image_field, overwrite=overwrite
                                    )
                                    if result_success is True:
                                        success, message = True, result_msg
                                        logger.info(f"✅ Fallback URL succeeded: {url[:80]}")
                                        break
                                    if result_success == "skipped":
                                        success, message = "skipped", result_msg
                                        break
                                except Exception as e:
                                    logger.debug(f"Fallback URL failed: {e}")
                
                except Exception as e:
                    logger.error(f"Search mode error: {e}", exc_info=True)
                    message = f"Lỗi chế độ tìm kiếm: {e}"
            
            logger.info(f"📌 Image processing result: success={repr(success)}, msg={message}")

            if success is True:
                logger.info(
                    f"✅ Note modified, will be saved by background processor: {vocabulary}"
                )
            elif success == "skipped":
                logger.info(f"⏭️ Note skipped (no DB update): {vocabulary}")
            else:
                logger.warning(f"📌 Image processing failed: {message}")

            final = self._finalize_result(success, message, vocabulary)
            # #region agent log
            cursor_session_log(
                "__init__.py:AddImageTask.process_note",
                "finalize_result",
                {
                    "success_repr": repr(success),
                    "final_status": repr(final[0]),
                    "final_msg": str(final[1])[:200],
                },
                "E",
            )
            # #endregion
            return final
        
        except APIError as e:
            logger.error(f"API Error: {e}", exc_info=True)
            return False, f"API Error: {str(e)}"
        except ImageError as e:
            logger.error(f"Image Error: {e}", exc_info=True)
            return False, f"Image Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return False, f"Lỗi không xác định: {str(e)}"


def _ensure_ai_provider(browser: Browser) -> bool:
    """Return True if an AI keyword provider is configured."""
    has_groq = bool(config_manager.get("groq_api_key"))
    has_gemini = bool(config_manager.get("gemini_api_key"))
    if has_groq or has_gemini:
        return True
    reply = browser_menu_manager.show_question(
        "Cấu hình",
        "Chưa có AI provider (Groq hoặc Gemini).\nCấu hình ngay?",
    )
    if not reply:
        return False
    config_dialog = ConfigDialog(browser, existing_config=config_manager.get_all())
    if config_dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    try:
        config_manager.set_many(config_dialog.get_config())
    except ValueError as e:
        browser_menu_manager.show_error("Lỗi cấu hình", str(e))
        return False
    return bool(config_manager.get("groq_api_key")) or bool(
        config_manager.get("gemini_api_key")
    )


def _resolve_batch_fields(browser: Browser, first_note) -> Optional[tuple]:
    """Return (vocab, definition, examples, image) or None if cancelled."""
    model_name = first_note.note_type()["name"]
    available_fields = list(first_note.keys())
    cfg = config_manager.get_all()
    preset = get_preset(cfg, model_name)
    always_show = config_manager.get("always_show_field_dialog", False)

    if preset and not always_show:
        mode = preset.get("image_generation_mode")
        if mode:
            config_manager.config["image_generation_mode"] = mode
        return (
            preset["vocabulary_field"],
            preset["definition_field"],
            preset.get("examples_field", ""),
            preset["image_field"],
        )

    field_dialog = FieldSelectionDialog(
        model_name, available_fields, browser, initial=preset
    )
    if field_dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    vocab_field = field_dialog.selected_vocab_field
    definition_field = field_dialog.selected_definition_field
    examples_field = field_dialog.selected_examples_field
    image_field = field_dialog.selected_image_field

    if field_dialog.save_as_preset:
        presets = dict(cfg.get("note_type_presets") or {})
        presets[model_name] = build_preset(
            vocab_field,
            definition_field,
            examples_field,
            image_field,
            config_manager.get("image_generation_mode", "search"),
        )
        config_manager.set_many(
            {
                "vocabulary_field": vocab_field,
                "definition_field": definition_field,
                "examples_field": examples_field,
                "image_field": image_field,
                "note_type_presets": presets,
            }
        )
    else:
        config_manager.set_many(
            {
                "vocabulary_field": vocab_field,
                "definition_field": definition_field,
                "examples_field": examples_field,
                "image_field": image_field,
            }
        )
    return vocab_field, definition_field, examples_field, image_field


def _build_ai_provider():
    provider_config = config_manager.get_all()
    return AIImageProvider(
        gemini_key=config_manager.get("gemini_api_key", ""),
        gemini_backup_key=config_manager.get("gemini_backup_api_key", ""),
        gemini_keyword_backup=config_manager.get("gemini_keyword_api_key_backup", ""),
        gemini_eval_api_key_1=config_manager.get("gemini_eval_api_key_1", ""),
        gemini_eval_api_key_2=config_manager.get("gemini_eval_api_key_2", ""),
        gemini_eval_api_key_3=config_manager.get("gemini_eval_api_key_3", ""),
        gemini_eval_api_key_4=config_manager.get("gemini_eval_api_key_4", ""),
        gemini_eval_api_key_5=config_manager.get("gemini_eval_api_key_5", ""),
        gemini_eval_api_key_6=config_manager.get("gemini_eval_api_key_6", ""),
        gemini_eval_api_key_7=config_manager.get("gemini_eval_api_key_7", ""),
        groq_key=config_manager.get("groq_api_key", ""),
        use_ollama=config_manager.get("use_ollama", False),
        ollama_url=config_manager.get("ollama_url", "http://localhost:11434"),
        provider_config=provider_config,
        enable_smart_selection=config_manager.get("enable_smart_selection", True),
        enable_ai_evaluation=config_manager.get("enable_ai_evaluation", True),
        enable_ai_provider_routing=config_manager.get("enable_ai_provider_routing", True),
        max_concurrent_providers=config_manager.get("max_concurrent_providers", 6),
        enable_adaptive_delay=config_manager.get("enable_adaptive_delay", True),
        base_delay_ms=config_manager.get("base_delay_ms", 100),
        max_delay_ms=config_manager.get("max_delay_ms", 2000),
    )


def _run_batch_processing(
    browser: Browser,
    note_ids: list,
    vocab_field: str,
    definition_field: str,
    examples_field: str,
    image_field: str,
    *,
    batch_meta: Optional[dict] = None,
):
    """Start background image batch for note_ids."""
    try:
        ai_provider = _build_ai_provider()
    except APIError as e:
        browser_menu_manager.show_error("Lỗi API", str(e))
        return

    mode_key = config_manager.get("image_generation_mode", "search")
    if mode_key == "generate":
        blockers = ai_provider.get_imagen_blockers()
        if blockers:
            # #region agent log
            cursor_session_log(
                "__init__.py:_run_batch_processing",
                "imagen_preflight_blocked",
                {"blockers": blockers},
                "A",
                run_id="post-fix",
            )
            # #endregion
            browser_menu_manager.show_error(
                "Imagen chưa sẵn sàng",
                "Chế độ Tạo ảnh AI cần:\n\n"
                + "\n".join(f"• {b}" for b in blockers)
                + "\n\nMở Config → Cài đặt nâng cao → bật Imagen và điền API key.",
            )
            return
    mode_labels = {
        "search": "Tìm kiếm",
        "generate": "Tạo ảnh (Imagen)",
        "smart": "Thông minh",
    }
    confirm_msg = (
        f"Thêm ảnh cho {len(note_ids)} thẻ.\n\n"
        f"Chế độ: {mode_labels.get(mode_key, mode_key)}\n"
        f"Từ vựng → {vocab_field}\n"
        f"Ảnh → {image_field}\n\nTiếp tục?"
    )
    if not browser_menu_manager.show_question("Xác nhận", confirm_msg):
        return

    progress_dialog = ProgressDialog(len(note_ids), browser)
    progress_dialog.show()
    progress_dialog.set_cancel_callback(bg_processor.cancel)

    task = AddImageTask(
        ai_provider, image_handler, vocab_field, definition_field, examples_field, image_field
    )
    last_ui_update = [0.0]
    update_interval_ms = 400

    def on_progress(current, total, message):
        now = time.time() * 1000
        if (now - last_ui_update[0] < update_interval_ms) and current != total:
            return
        last_ui_update[0] = now

        def _update_ui():
            if progress_dialog.is_cancelled:
                return
            parts = message.split(" | ")
            progress_dialog.update_progress(
                current, total, parts[0], parts[1] if len(parts) > 1 else ""
            )

        mw.taskman.run_on_main(_update_ui)

    def on_success(result):
        results = result.get("results", [])
        errors = result.get("errors", [])
        pending = result.get("pending_note_ids") or []

        successful = skipped_results = failed_results = 0
        first_fail_msg = None
        for r in results:
            if not isinstance(r, tuple) or len(r) < 2:
                failed_results += 1
                if first_fail_msg is None:
                    first_fail_msg = repr(r)[:120]
                continue
            st = r[0]
            if st is True:
                successful += 1
            elif st == "skipped":
                skipped_results += 1
            else:
                failed_results += 1
                if first_fail_msg is None:
                    first_fail_msg = str(r[1])[:200]
        failed_results += len(errors)
        # #region agent log
        cursor_session_log(
            "__init__.py:_run_batch_processing.on_success",
            "batch_summary",
            {
                "successful": successful,
                "skipped": skipped_results,
                "failed": failed_results,
                "first_fail_msg": first_fail_msg,
                "errors": errors[:3] if errors else [],
            },
            "E",
        )
        # #endregion

        meta = batch_meta or {
            "vocabulary_field": vocab_field,
            "definition_field": definition_field,
            "examples_field": examples_field,
            "image_field": image_field,
        }
        if pending:
            config_manager.set_many(
                {
                    "pending_batch_note_ids": pending,
                    "pending_batch_meta": meta,
                }
            )
        elif not progress_dialog.is_cancelled:
            config_manager.clear_pending_batch()

        def _finish_ui():
            progress_dialog.finish(successful, skipped_results, failed_results)
            summary = (
                f"Thành công: {successful}\n"
                f"Bỏ qua: {skipped_results}\n"
                f"Thất bại: {failed_results}"
            )
            if first_fail_msg and failed_results:
                summary += f"\n\nLý do: {first_fail_msg}"
            if pending:
                summary += f"\n\n⏸ Đã lưu {len(pending)} thẻ — dùng menu «Tiếp tục batch đã dừng»."
            progress_dialog.detail_label.setText(summary)

        mw.taskman.run_on_main(_finish_ui)

        def refresh_browser():
            try:
                browser.search()
            except Exception:
                pass

        QTimer.singleShot(1000, refresh_browser)

    def on_error(error_msg):
        def _error_ui():
            progress_dialog.reject()
            browser_menu_manager.show_error("Lỗi", error_msg)

        mw.taskman.run_on_main(_error_ui)

    bg_processor.process_cards_in_background(
        note_ids,
        lambda note: task.process_note(note),
        on_progress=on_progress,
        on_success=on_success,
        on_error=on_error,
        title=f"AnkiAI ({len(note_ids)} thẻ)",
    )


def on_browser_menu_resume_batch(browser: Browser):
    config_manager.reload()
    pending = config_manager.get("pending_batch_note_ids") or []
    meta = config_manager.get("pending_batch_meta") or {}
    if not pending:
        browser_menu_manager.show_info(
            "AnkiAI", "Không có batch nào đang chờ tiếp tục."
        )
        return
    if not _ensure_ai_provider(browser):
        return
    _run_batch_processing(
        browser,
        pending,
        meta.get("vocabulary_field", config_manager.get("vocabulary_field")),
        meta.get("definition_field", config_manager.get("definition_field")),
        meta.get("examples_field", config_manager.get("examples_field")),
        meta.get("image_field", config_manager.get("image_field")),
        batch_meta=meta,
    )


def on_browser_menu_add_images(browser: Browser):
    """Browser menu: add images to selected notes."""
    note_ids = browser_menu_manager.get_selected_note_ids(browser)
    if not note_ids:
        browser_menu_manager.show_warning("Cảnh báo", "Vui lòng chọn ít nhất 1 thẻ")
        return

    config_manager.reload()

    if not _ensure_ai_provider(browser):
        return

    pending = config_manager.get("pending_batch_note_ids") or []
    batch_dialog = BatchOptionsDialog(
        len(note_ids),
        default_max=int(config_manager.get("max_notes_per_batch", 100)),
        pending_count=len(pending),
        parent=browser,
    )
    if batch_dialog.exec() != QDialog.DialogCode.Accepted:
        return

    if batch_dialog.use_pending and pending:
        on_browser_menu_resume_batch(browser)
        return

    max_n = batch_dialog.max_notes
    if max_n > 0 and len(note_ids) > max_n:
        note_ids = note_ids[:max_n]

    try:
        first_note = mw.col.get_note(note_ids[0])
    except Exception as e:
        browser_menu_manager.show_error("Lỗi", f"Không thể lấy note: {e}")
        return

    fields = _resolve_batch_fields(browser, first_note)
    if not fields:
        return
    vocab_field, definition_field, examples_field, image_field = fields

    _run_batch_processing(
        browser,
        note_ids,
        vocab_field,
        definition_field,
        examples_field,
        image_field,
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
            config_manager.set_many(config)
            
            logger.info(f"[open_config_dialog] Config saved successfully")
            QMessageBox.information(mw, "AnkiAI", "Đã lưu cấu hình thành công! ✓")
        except ValueError as e:
            QMessageBox.warning(mw, "Lỗi cấu hình", str(e))


def on_config_changed(new_config):
    """Callback khi config thay đổi từ Anki JSON editor"""
    global config_manager
    if config_manager is not None:
        config_manager.config = new_config
        configure_debug_log(
            enabled=bool(new_config.get("enable_agent_debug_log", False)),
        )
        logger.info("[ADDON] Config updated from Anki editor")


def setup_addon():
    """Setup add-on khi Anki khởi động"""
    global browser_menu_manager, image_handler, bg_processor, config_manager, feature_db, advanced_features
    
    logger.info("[ADDON] Initializing AnkiAI...")
    
    try:
        # Khởi tạo các components
        config_manager = get_config_manager()
        configure_debug_log(
            enabled=bool(config_manager.get("enable_agent_debug_log", False)),
        )
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
                on_browser_menu_add_images,
                on_browser_menu_resume_batch,
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
            from .modules.providers.base import _ImageProviderSessionManager
            _ImageProviderSessionManager.close_all()
            logger.info("[ADDON] Image provider sessions closed (20-30% resource savings)")
        except Exception as e:
            logger.error(f"[ADDON] Warning: Could not close image provider sessions: {e}")

        try:
            HTTPSessionManager.close_all()
            logger.info("[ADDON] Central HTTP sessions closed")
        except Exception as e:
            logger.error(f"[ADDON] Warning: Could not close central HTTP sessions: {e}")
        
        # Stop background processor if running
        if bg_processor and hasattr(bg_processor, 'cancel'):
            bg_processor.cancel()
            logger.info("[ADDON] Background processor stopped")
        
        # Close feature database
        if feature_db and hasattr(feature_db, 'close'):
            feature_db.close()
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
