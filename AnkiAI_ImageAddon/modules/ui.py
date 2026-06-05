"""
UI Handler Module - Giao diện người dùng & Browser Context Menu
Giai đoạn 1: Tạo menu trong Browser và trích xuất dữ liệu thẻ
"""

from aqt import mw
from aqt.browser import Browser
from aqt.qt import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QWidget,
    QProgressBar,
    QLineEdit,
    QTextBrowser,
    QCheckBox,
    QSpinBox,
)
from typing import List, Optional, Callable, Dict, Any
from .ui_theme import apply_dialog_theme
from .ui_widgets import (
    make_settings_card,
    card_header,
    field_row,
    password_field,
    section_spacer,
)
import functools
import logging
import requests
import re

# Configure logging
logger = logging.getLogger(__name__)


class BrowserMenuManager:
    """Quản lý context menu trong Browser"""
    
    def __init__(self):
        """Khởi tạo BrowserMenuManager"""
        self.browser: Optional[Browser] = None
    
    def setup_browser_menu(
        self,
        browser: Browser,
        callback_add_images: callable,
        callback_resume_batch: Optional[callable] = None,
    ):
        """
        Hook vào Browser để thêm context menu
        
        Cách dùng: Người dùng bôi đen 100 thẻ, nhấn phải chuột, chọn "Tự động thêm ảnh bằng AI"
        
        Args:
            browser: Anki Browser window
            callback_add_images: Function được gọi khi người dùng chọn menu
        """
        self.browser = browser
        
        # Lấy danh sách các action trong context menu
        # Phiên bản cũ: browser.form.searchEdit.customContextMenuRequested.connect()
        # Phiên bản mới: Hook browser_menus_did_init
        
        # Tạo action cho menu
        try:
            # Phương pháp mới (Anki 24.04+)
            action = browser.form.menu_Cards.addAction("AnkiAI: Tự động thêm ảnh")
            action.triggered.connect(lambda: callback_add_images(browser))
            if callback_resume_batch:
                resume = browser.form.menu_Cards.addAction("AnkiAI: Tiếp tục batch đã dừng")
                resume.triggered.connect(lambda: callback_resume_batch(browser))
            logger.info("Menu added to Cards menu")
        except Exception as e1:
            logger.warning(f"Failed to add to Cards menu: {e1}")
            # Thử menu_Notes (Anki 25+)
            try:
                action = browser.form.menu_Notes.addAction("AnkiAI: Tự động thêm ảnh")
                action.triggered.connect(lambda: callback_add_images(browser))
                if callback_resume_batch:
                    resume = browser.form.menu_Notes.addAction(
                        "AnkiAI: Tiếp tục batch đã dừng"
                    )
                    resume.triggered.connect(lambda: callback_resume_batch(browser))
                logger.info("Menu added to Notes menu")
            except Exception as e2:
                logger.warning(f"Failed to add to Notes menu: {e2}")
                # Fallback: Dùng phương pháp cũ
                try:
                    action = browser.menuBar().addAction("AnkiAI: Tự động thêm ảnh")
                    action.triggered.connect(lambda: callback_add_images(browser))
                    logger.info("Menu added to menuBar")
                except Exception as e3:
                        logger.error(f"Error setting up browser menu: {e3}")
    def get_selected_note_ids(self, browser: Browser) -> List[int]:
        """
        Lấy danh sách Note IDs của các thẻ được chọn
        
        Args:
            browser: Anki Browser window
        
        Returns:
            Danh sách Note IDs
        """
        try:
            # Cách lấy thẻ được chọn trong Browser
            selected_cids = browser.selected_cards()
            
            if not selected_cids:
                return []
            
            # Convert card IDs sang Note IDs
            note_ids = set()
            for cid in selected_cids:
                card = mw.col.get_card(cid)
                note_ids.add(card.nid)
            
            return list(note_ids)
        
        except Exception as e:
            logger.warning(f"Error getting selected note IDs: {e}")
            return []
    
    def show_error(self, title: str, message: str):
        """Hiển thị lỗi"""
        QMessageBox.critical(self.browser, title, message)
    
    def show_warning(self, title: str, message: str):
        """Hiển thị cảnh báo"""
        QMessageBox.warning(self.browser, title, message)
    
    def show_info(self, title: str, message: str):
        """Hiển thị thông tin"""
        QMessageBox.information(self.browser, title, message)
    
    def show_question(self, title: str, message: str) -> bool:
        """Hiển thị câu hỏi, trả về True nếu người dùng chọn Yes"""
        reply = QMessageBox.question(self.browser, title, message)
        return reply == QMessageBox.StandardButton.Yes


class BatchOptionsDialog(QDialog):
    """Giới hạn số thẻ / tiếp tục batch trước."""

    def __init__(
        self,
        selected_count: int,
        default_max: int = 100,
        pending_count: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.use_pending = False
        self.max_notes = selected_count
        apply_dialog_theme(self)
        self.setWindowTitle("AnkiAI — Tùy chọn batch")
        self.setMinimumWidth(420)

        layout = QVBoxLayout()
        title = QLabel(f"Đã chọn {selected_count} thẻ")
        title.setProperty("heading", True)
        layout.addWidget(title)

        hint = QLabel(
            "Giới hạn mỗi lần chạy giúp addon mượt hơn và tránh rate limit API."
        )
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Tối đa mỗi lần (0 = tất cả):"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(0, max(selected_count, 1))
        self.max_spin.setValue(
            min(default_max, selected_count) if default_max > 0 else selected_count
        )
        row.addWidget(self.max_spin)
        layout.addLayout(row)

        self.pending_btn = None
        if pending_count > 0:
            self.pending_btn = QPushButton(
                f"Tiếp tục batch đã dừng ({pending_count} thẻ)"
            )
            self.pending_btn.setProperty("primary", True)
            self.pending_btn.clicked.connect(self._accept_pending)
            layout.addWidget(self.pending_btn)

        buttons = QHBoxLayout()
        ok = QPushButton("Tiếp tục")
        ok.setProperty("primary", True)
        cancel = QPushButton("Hủy")
        ok.clicked.connect(self._accept_normal)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(ok)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def _accept_normal(self):
        self.use_pending = False
        self.max_notes = self.max_spin.value()
        self.accept()

    def _accept_pending(self):
        self.use_pending = True
        self.accept()


class FieldSelectionDialog(QDialog):
    """Dialog cho người dùng chọn các field"""
    
    def __init__(
        self,
        model_name: str,
        available_fields: List[str],
        parent=None,
        initial: Optional[Dict[str, str]] = None,
    ):
        """
        Khởi tạo FieldSelectionDialog
        
        Args:
            model_name: Tên của Note Type
            available_fields: Danh sách các field có sẵn
            parent: Parent widget
        """
        super().__init__(parent)
        self.available_fields = available_fields
        self.selected_vocab_field = None
        self.selected_definition_field = None
        self.selected_examples_field = None  # ✨ NEW: Examples field
        self.selected_image_field = None
        self.save_as_preset = False
        self._initial = initial or {}
        
        self.init_ui(model_name)
    
    def init_ui(self, model_name: str):
        """Tạo giao diện dialog"""
        apply_dialog_theme(self)
        self.setWindowTitle(f"AnkiAI — Fields · {model_name}")
        self.setMinimumWidth(440)
        
        layout = QVBoxLayout()
        head = QLabel(f"Note type: {model_name}")
        head.setProperty("heading", True)
        layout.addWidget(head)
        
        def _combo(fields, key, defaults):
            combo = QComboBox()
            combo.addItems(fields)
            val = self._initial.get(key) or ""
            if val and val in fields:
                combo.setCurrentText(val)
            elif defaults in fields:
                combo.setCurrentText(defaults)
            return combo

        layout.addWidget(QLabel("Field từ vựng"))
        vocab_combo = _combo(self.available_fields, "vocabulary_field", "Mặt trước")
        layout.addWidget(vocab_combo)
        
        layout.addWidget(QLabel("Field định nghĩa"))
        definition_combo = _combo(self.available_fields, "definition_field", "Định nghĩa")
        layout.addWidget(definition_combo)
        
        layout.addWidget(QLabel("Field ví dụ (tùy chọn)"))
        examples_combo = QComboBox()
        examples_combo.addItems([""] + self.available_fields)
        ex = self._initial.get("examples_field", "")
        if ex and ex in self.available_fields:
            examples_combo.setCurrentText(ex)
        elif "Ví dụ" in self.available_fields:
            examples_combo.setCurrentText("Ví dụ")
        layout.addWidget(examples_combo)
        
        layout.addWidget(QLabel("Field ảnh"))
        image_combo = _combo(self.available_fields, "image_field", "Ảnh")
        layout.addWidget(image_combo)

        self.remember_checkbox = QCheckBox(
            "Lưu preset cho note type này (lần sau không hỏi lại)"
        )
        self.remember_checkbox.setChecked(True)
        layout.addWidget(self.remember_checkbox)
        
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Hủy")
        ok_button = QPushButton("Tiếp tục")
        ok_button.setProperty("primary", True)
        
        ok_button.clicked.connect(lambda: self.accept_with_values(
            vocab_combo.currentText(),
            definition_combo.currentText(),
            examples_combo.currentText(),
            image_combo.currentText()
        ))
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def accept_with_values(self, vocab_field: str, definition_field: str, examples_field: str, image_field: str):
        """Lưu lựa chọn và đóng dialog"""
        self.selected_vocab_field = vocab_field
        self.selected_definition_field = definition_field
        self.selected_examples_field = examples_field
        self.selected_image_field = image_field
        self.save_as_preset = self.remember_checkbox.isChecked()
        self.accept()


class ConfigDialog(QDialog):
    """Dialog cài đặt API keys"""
    
    def __init__(self, parent=None, existing_config=None):
        """Khởi tạo ConfigDialog"""
        super().__init__(parent)
        self.config_values = {}
        self.existing_config = existing_config or {}
        self.init_ui()
        self.load_existing_config()
    
    def init_ui(self):
        """Tạo giao diện config — dark theme, card layout."""
        from aqt.qt import QLineEdit, QCheckBox, QScrollArea, QWidget, QFrame

        apply_dialog_theme(self)
        self.setWindowTitle("AnkiAI v5.1 — Cài đặt")
        self.setMinimumWidth(680)
        self.setMinimumHeight(720)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 18, 20, 16)
        main_layout.setSpacing(12)

        header = QLabel("AnkiAI v5.1 — Cài đặt")
        header.setProperty("heading", True)
        main_layout.addWidget(header)
        rule = QFrame()
        rule.setObjectName("headerRule")
        rule.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(rule)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_body = QWidget()
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(4, 8, 4, 8)
        scroll_layout.setSpacing(14)

        # —— Card 1: Chế độ hoạt động ——
        c1, l1 = make_settings_card()
        l1.addWidget(card_header("🎨", "Chế độ hoạt động"))
        l1.addWidget(
            field_row(
                "Chế độ chính",
                "Search: tìm ảnh nhanh. Generate: Imagen. Smart: ưu tiên AI, fallback tìm kiếm.",
            )
        )
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Tìm kiếm ảnh (Search)", "search")
        self.mode_combo.addItem("Tạo ảnh AI (Imagen)", "generate")
        self.mode_combo.addItem("Thông minh (Smart)", "smart")
        self.mode_combo.setToolTip("Cách addon lấy ảnh cho mỗi thẻ.")
        l1.addWidget(self.mode_combo)
        scroll_layout.addWidget(c1)

        # —— Card 2: Nhà cung cấp AI ——
        c2, l2 = make_settings_card()
        l2.addWidget(card_header("🤖", "Nhà cung cấp AI"))
        l2.addWidget(
            field_row(
                "Groq API Key",
                "Nhanh, miễn phí — dùng để tạo từ khóa tìm ảnh.",
                badge="recommended",
            )
        )
        self.groq_input = password_field("console.groq.com/keys")
        l2.addWidget(self.groq_input)

        l2.addWidget(section_spacer())
        l2.addWidget(
            field_row(
                "Gemini Key #1",
                "Key chính để tạo từ khóa và ngữ cảnh tìm kiếm.",
                badge="priority",
            )
        )
        self.gemini_input = password_field("aistudio.google.com/apikey")
        l2.addWidget(self.gemini_input)

        l2.addWidget(field_row("Gemini Key #2", "Dự phòng 1 khi key #1 bị giới hạn."))
        self.gemini_backup_input = password_field("Tùy chọn")
        l2.addWidget(self.gemini_backup_input)

        l2.addWidget(field_row("Gemini Key #3", "Dự phòng 2 cho tạo từ khóa."))
        self.gemini_keyword_backup_input = password_field("Tùy chọn")
        l2.addWidget(self.gemini_keyword_backup_input)

        l2.addWidget(section_spacer())
        ollama_row = QHBoxLayout()
        self.ollama_checkbox = QCheckBox("Sử dụng Ollama local")
        self.ollama_checkbox.setToolTip("Chạy trên máy — ollama pull mistral")
        ollama_row.addWidget(self.ollama_checkbox)
        ollama_row.addStretch()
        l2.addLayout(ollama_row)
        l2.addWidget(field_row("Địa chỉ Ollama", "Máy chủ local mặc định."))
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setText("http://localhost:11434")
        l2.addWidget(self.ollama_url_input)
        scroll_layout.addWidget(c2)

        # —— Card 3: Tìm kiếm hình ảnh ——
        c3, l3 = make_settings_card()
        l3.addWidget(card_header("📷", "Dịch vụ tìm kiếm hình ảnh"))
        l3.addWidget(
            field_row("Pexels", "Ảnh stock chất lượng cao.", badge="recommended")
        )
        self.pexels_input = password_field("pexels.com/api")
        l3.addWidget(self.pexels_input)

        l3.addWidget(field_row("Pixabay", "Miễn phí, phù hợp flashcard.", badge="recommended"))
        self.pixabay_input = password_field("pixabay.com/api")
        l3.addWidget(self.pixabay_input)

        l3.addWidget(field_row("Unsplash", "Tùy chọn — bộ sưu tập lớn."))
        self.unsplash_input = password_field("unsplash.com/developers")
        l3.addWidget(self.unsplash_input)

        l3.addWidget(field_row("Europeana", "Di sản văn hóa châu Âu — tùy chọn."))
        self.europeana_input = password_field("pro.europeana.eu")
        l3.addWidget(self.europeana_input)

        l3.addWidget(section_spacer())
        l3.addWidget(card_header("🎬", "Ảnh động / GIF"))
        l3.addWidget(field_row("KLIPY", "GIF có hỗ trợ localization.", badge="recommended"))
        self.klipy_input = password_field("klipy.io/developers")
        l3.addWidget(self.klipy_input)
        l3.addWidget(field_row("GIPHY", "Thư viện GIF lớn."))
        self.giphy_input = password_field("developers.giphy.com")
        l3.addWidget(self.giphy_input)
        l3.addWidget(field_row("Tenor", "Hết hạn API dự kiến 30/06/2026."))
        self.tenor_input = password_field("Google Cloud Console")
        l3.addWidget(self.tenor_input)
        l3.addWidget(field_row("IconScout", "Icon và Lottie động."))
        self.iconscout_input = password_field("iconscout.com/api")
        l3.addWidget(self.iconscout_input)
        scroll_layout.addWidget(c3)

        # —— Card 4: Nâng cao ——
        c4, l4 = make_settings_card()
        l4.addWidget(card_header("⚙️", "Cài đặt nâng cao"))

        self.enable_ai_eval_checkbox = QCheckBox(
            "Gemini Vision — chọn ảnh tốt nhất trong các ứng viên"
        )
        self.enable_ai_eval_checkbox.setChecked(True)
        l4.addWidget(self.enable_ai_eval_checkbox)

        self.gemini_eval_inputs = []
        _eval_hints = [
            "Key đầu tiên dùng để đánh giá ảnh.",
            "Backup khi key #1 bị giới hạn.",
            "Backup #2", "Backup #3", "Backup #4", "Backup #5", "Backup #6",
        ]
        for i in range(1, 8):
            badge = "priority" if i == 1 else ""
            l4.addWidget(field_row(f"Gemini Eval Key #{i}", _eval_hints[i - 1], badge=badge))
            inp = password_field("Để trống nếu không dùng")
            l4.addWidget(inp)
            self.gemini_eval_inputs.append(inp)

        l4.addWidget(section_spacer())
        l4.addWidget(card_header("🔮", "Tạo ảnh Imagen"))
        self.enable_imagen_checkbox = QCheckBox("Bật tạo ảnh bằng Imagen")
        l4.addWidget(self.enable_imagen_checkbox)
        l4.addWidget(field_row("Imagen API Key", "Google AI Studio."))
        self.imagen_api_key_input = password_field("aistudio.google.com")
        l4.addWidget(self.imagen_api_key_input)

        self.enable_gemini_desc_checkbox = QCheckBox(
            "Gemini viết mô tả chi tiết (prompt) cho Imagen"
        )
        self.enable_gemini_desc_checkbox.setChecked(True)
        l4.addWidget(self.enable_gemini_desc_checkbox)
        l4.addWidget(field_row("Gemini mô tả ảnh — Key chính", badge="priority"))
        self.gemini_desc_input = password_field("aistudio.google.com")
        l4.addWidget(self.gemini_desc_input)
        l4.addWidget(field_row("Gemini mô tả — Backup 1"))
        self.gemini_desc_backup1_input = password_field("Tùy chọn")
        l4.addWidget(self.gemini_desc_backup1_input)
        l4.addWidget(field_row("Gemini mô tả — Backup 2"))
        self.gemini_desc_backup2_input = password_field("Tùy chọn")
        l4.addWidget(self.gemini_desc_backup2_input)

        l4.addWidget(field_row("Phong cách mặc định"))
        self.imagen_style_combo = QComboBox()
        self.imagen_style_combo.addItems(
            ["photorealistic", "illustration", "cartoon", "painting", "3d"]
        )
        l4.addWidget(self.imagen_style_combo)
        l4.addWidget(field_row("Kích thước mặc định"))
        self.imagen_size_combo = QComboBox()
        self.imagen_size_combo.addItems(["1024x1024", "512x512", "256x256", "1536x1536"])
        l4.addWidget(self.imagen_size_combo)
        self.imagen_fallback_checkbox = QCheckBox(
            "Fallback sang tìm kiếm nếu Imagen lỗi"
        )
        self.imagen_fallback_checkbox.setChecked(True)
        l4.addWidget(self.imagen_fallback_checkbox)

        l4.addWidget(section_spacer())
        self.enable_rate_limit_checkbox = QCheckBox(
            "Tự dừng khi API trả về rate limit (429)"
        )
        self.enable_rate_limit_checkbox.setChecked(True)
        l4.addWidget(self.enable_rate_limit_checkbox)
        l4.addWidget(field_row("Thời gian tạm dừng (giây)"))
        self.rate_limit_pause_input = QLineEdit()
        self.rate_limit_pause_input.setText("60")
        l4.addWidget(self.rate_limit_pause_input)

        self.skip_existing_images_checkbox = QCheckBox(
            "Bỏ qua thẻ đã có ảnh trong field"
        )
        self.skip_existing_images_checkbox.setChecked(True)
        l4.addWidget(self.skip_existing_images_checkbox)

        l4.addWidget(section_spacer())
        test_row = QHBoxLayout()
        test_ai_button = QPushButton("Kiểm tra AI")
        test_ai_button.clicked.connect(self.test_connection)
        test_image_button = QPushButton("Kiểm tra nguồn ảnh")
        test_image_button.clicked.connect(self.test_image_providers)
        test_row.addWidget(test_ai_button)
        test_row.addWidget(test_image_button)
        l4.addLayout(test_row)
        scroll_layout.addWidget(c4)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_body)
        main_layout.addWidget(scroll, stretch=1)

        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Hủy")
        ok_button = QPushButton("Lưu cấu hình")
        ok_button.setProperty("primary", True)
        cancel_button.clicked.connect(self.reject)
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def load_existing_config(self):
        """Load existing config values into input fields"""
        try:
            if self.existing_config:
                # Load AI Provider Keys
                groq_key = self.existing_config.get("groq_api_key", "")
                if groq_key:
                    self.groq_input.setText(groq_key)
                
                gemini_key = self.existing_config.get("gemini_api_key", "")
                if gemini_key:
                    self.gemini_input.setText(gemini_key)
                
                # ✨ Load backup Gemini keys for keyword generation
                gemini_backup_key = self.existing_config.get("gemini_backup_api_key", "")
                if gemini_backup_key:
                    self.gemini_backup_input.setText(gemini_backup_key)
                
                gemini_keyword_backup_key = self.existing_config.get("gemini_keyword_api_key_backup", "")
                if gemini_keyword_backup_key:
                    self.gemini_keyword_backup_input.setText(gemini_keyword_backup_key)
                
                gemini_keyword_backup_key = self.existing_config.get("gemini_keyword_api_key_backup", "")
                if gemini_keyword_backup_key:
                    self.gemini_keyword_backup_input.setText(gemini_keyword_backup_key)
                
                use_ollama = self.existing_config.get("use_ollama", False)
                self.ollama_checkbox.setChecked(use_ollama)
                
                ollama_url = self.existing_config.get("ollama_url", "http://localhost:11434")
                self.ollama_url_input.setText(ollama_url)
                
                # Load Image Search Provider Keys
                unsplash_key = self.existing_config.get("unsplash_api_key", "")
                if unsplash_key:
                    self.unsplash_input.setText(unsplash_key)
                
                pexels_key = self.existing_config.get("pexels_api_key", "")
                if pexels_key:
                    self.pexels_input.setText(pexels_key)
                
                pixabay_key = self.existing_config.get("pixabay_api_key", "")
                if pixabay_key:
                    self.pixabay_input.setText(pixabay_key)
                
                # ✨ Load new provider keys (v4.2)
                europeana_key = self.existing_config.get("europeana_api_key", "")
                if europeana_key:
                    self.europeana_input.setText(europeana_key)
                
                # 🆕 v4.4: Load 7 Gemini Eval API keys
                enable_ai_eval = self.existing_config.get("enable_ai_evaluation", True)
                self.enable_ai_eval_checkbox.setChecked(enable_ai_eval)
                
                for i in range(1, 8):
                    key = self.existing_config.get(f"gemini_eval_api_key_{i}", "")
                    if key:
                        self.gemini_eval_inputs[i-1].setText(key)
                
                # ✨ Load rate limit protection settings (v4.2)
                enable_rate_limit = self.existing_config.get("enable_rate_limit_protection", True)
                self.enable_rate_limit_checkbox.setChecked(enable_rate_limit)
                
                rate_limit_pause = self.existing_config.get("rate_limit_pause_duration", 60)
                self.rate_limit_pause_input.setText(str(rate_limit_pause))

                # ✨ Load v5.0 Image Generation Mode
                mode = self.existing_config.get("image_generation_mode", "search")
                index = self.mode_combo.findData(mode)
                if index >= 0:
                    self.mode_combo.setCurrentIndex(index)
                
                # ✨ Load v5.0 GIF providers
                klipy_key = self.existing_config.get("klipy_app_key", "")
                self.klipy_input.setText(klipy_key)
                giphy_key = self.existing_config.get("giphy_api_key", "")
                self.giphy_input.setText(giphy_key)
                tenor_key = self.existing_config.get("tenor_api_key", "")
                self.tenor_input.setText(tenor_key)
                iconscout_token = self.existing_config.get("iconscout_api_token", "")
                self.iconscout_input.setText(iconscout_token)
                
                # ✨ Load v5.0 Imagen AI Settings
                enable_imagen = self.existing_config.get("imagen_enabled", False)
                self.enable_imagen_checkbox.setChecked(enable_imagen)
                
                imagen_key = self.existing_config.get("imagen_api_key", "")
                self.imagen_api_key_input.setText(imagen_key)
                
                enable_gemini_desc = self.existing_config.get("enable_gemini_image_description", True)
                self.enable_gemini_desc_checkbox.setChecked(enable_gemini_desc)
                
                gemini_desc_key = self.existing_config.get("gemini_image_description_api_key", "")
                self.gemini_desc_input.setText(gemini_desc_key)
                
                gemini_desc_backup1 = self.existing_config.get("gemini_image_description_api_key_backup_1", "")
                self.gemini_desc_backup1_input.setText(gemini_desc_backup1)
                
                gemini_desc_backup2 = self.existing_config.get("gemini_image_description_api_key_backup_2", "")
                self.gemini_desc_backup2_input.setText(gemini_desc_backup2)
                
                style = self.existing_config.get("imagen_default_style", "photorealistic")
                self.imagen_style_combo.setCurrentText(style)
                
                size = self.existing_config.get("imagen_default_size", "1024x1024")
                self.imagen_size_combo.setCurrentText(size)
                
                imagen_fallback = self.existing_config.get("imagen_fallback_to_search_providers", True)
                self.imagen_fallback_checkbox.setChecked(imagen_fallback)

                # ✨ Load v5.1 skip_existing_images
                skip_existing = self.existing_config.get("skip_existing_images", True)
                self.skip_existing_images_checkbox.setChecked(skip_existing)
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
    
    def get_config(self) -> dict:
        """Lấy cấu hình từ dialog"""
        groq_key = self.groq_input.text().strip()
        gemini_key = self.gemini_input.text().strip()
        gemini_backup_key = self.gemini_backup_input.text().strip()
        gemini_keyword_backup_key = self.gemini_keyword_backup_input.text().strip()  # ✨ NEW v4.2
        use_ollama = self.ollama_checkbox.isChecked()
        
        # Validate: at least one AI provider is configured
        if not groq_key and not gemini_key and not use_ollama:
            raise ValueError("Vui lòng cấu hình ít nhất một AI provider (Groq, Gemini, hoặc Ollama)")
        
        # Image providers (Optional check as free ones are always available)
        pexels_key = self.pexels_input.text().strip()
        unsplash_key = self.unsplash_input.text().strip()
        pixabay_key = self.pixabay_input.text().strip()
        europeana_key = self.europeana_input.text().strip()  # ✨ NEW v4.2
        
        # 🆕 v4.4: Get 7 Gemini Eval API keys
        enable_ai_eval = self.enable_ai_eval_checkbox.isChecked()
        gemini_eval_keys = {}
        for i in range(1, 8):
            key = self.gemini_eval_inputs[i-1].text().strip()
            gemini_eval_keys[f"gemini_eval_api_key_{i}"] = key
        
        # ✨ NEW v4.2: Rate limit protection
        enable_rate_limit = self.enable_rate_limit_checkbox.isChecked()
        try:
            rate_limit_pause = int(self.rate_limit_pause_input.text().strip() or "60")
        except ValueError:
            rate_limit_pause = 60
        
        # ✨ NEW v5.0 settings
        mode = self.mode_combo.currentData() or "search"
        klipy_key = self.klipy_input.text().strip()
        giphy_key = self.giphy_input.text().strip()
        tenor_key = self.tenor_input.text().strip()
        iconscout_token = self.iconscout_input.text().strip()
        
        enable_imagen = self.enable_imagen_checkbox.isChecked()
        imagen_key = self.imagen_api_key_input.text().strip()
        enable_gemini_desc = self.enable_gemini_desc_checkbox.isChecked()
        # Chế độ Generate bắt buộc bật Imagen + mô tả Gemini
        if mode == "generate":
            enable_imagen = True
            enable_gemini_desc = True
        gemini_desc_key = self.gemini_desc_input.text().strip()
        gemini_desc_backup1 = self.gemini_desc_backup1_input.text().strip()
        gemini_desc_backup2 = self.gemini_desc_backup2_input.text().strip()
        style = self.imagen_style_combo.currentText()
        size = self.imagen_size_combo.currentText()
        imagen_fallback = self.imagen_fallback_checkbox.isChecked()
        
        # ✨ NEW v5.1 skip_existing_images
        skip_existing = self.skip_existing_images_checkbox.isChecked()

        return {
            "groq_api_key": groq_key,
            "gemini_api_key": gemini_key,
            "gemini_backup_api_key": gemini_backup_key,
            "gemini_keyword_api_key_backup": gemini_keyword_backup_key,  # ✨ NEW v4.2
            # 🆕 v4.4: 7 Gemini Image Evaluator API keys
            "gemini_eval_api_key_1": gemini_eval_keys.get("gemini_eval_api_key_1", ""),
            "gemini_eval_api_key_2": gemini_eval_keys.get("gemini_eval_api_key_2", ""),
            "gemini_eval_api_key_3": gemini_eval_keys.get("gemini_eval_api_key_3", ""),
            "gemini_eval_api_key_4": gemini_eval_keys.get("gemini_eval_api_key_4", ""),
            "gemini_eval_api_key_5": gemini_eval_keys.get("gemini_eval_api_key_5", ""),
            "gemini_eval_api_key_6": gemini_eval_keys.get("gemini_eval_api_key_6", ""),
            "gemini_eval_api_key_7": gemini_eval_keys.get("gemini_eval_api_key_7", ""),
            "enable_ai_evaluation": enable_ai_eval,  # 🆕 v4.4: Re-enabled
            "use_ollama": use_ollama,
            "ollama_url": self.ollama_url_input.text().strip(),
            "unsplash_api_key": unsplash_key,
            "pexels_api_key": pexels_key,
            "pixabay_api_key": pixabay_key,
            "europeana_api_key": europeana_key,  # ✨ NEW v4.2
            "enable_rate_limit_protection": enable_rate_limit,  # ✨ NEW v4.2
            "rate_limit_pause_duration": rate_limit_pause,  # ✨ NEW v4.2
            
            # ✨ NEW v5.0
            "image_generation_mode": mode,
            "klipy_app_key": klipy_key,
            "giphy_api_key": giphy_key,
            "tenor_api_key": tenor_key,
            "iconscout_api_token": iconscout_token,
            
            "imagen_enabled": enable_imagen,
            "imagen_api_key": imagen_key,
            "enable_gemini_image_description": enable_gemini_desc,
            "gemini_image_description_api_key": gemini_desc_key,
            "gemini_image_description_api_key_backup_1": gemini_desc_backup1,
            "gemini_image_description_api_key_backup_2": gemini_desc_backup2,
            "imagen_default_style": style,
            "imagen_default_size": size,
            "imagen_fallback_to_search_providers": imagen_fallback,
            
            # ✨ NEW v5.1 skip_existing_images
            "skip_existing_images": skip_existing
        }
    
    def test_connection(self):
        """Test kết nối AI providers"""
        groq_key = self.groq_input.text().strip()
        gemini_key = self.gemini_input.text().strip()
        use_ollama = self.ollama_checkbox.isChecked()
        ollama_url = self.ollama_url_input.text().strip()
        
        if not (groq_key or gemini_key or use_ollama):
            QMessageBox.warning(self, "Lỗi", "Vui lòng cấu hình ít nhất một AI provider")
            return
        
        results = []
        
        # Test Groq
        if groq_key:
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 5
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    results.append("✓ Groq API: OK")
                else:
                    results.append(f"✗ Groq API: Error {response.status_code}")
            except Exception as e:
                results.append(f"✗ Groq API: {str(e)}")
        
        # Test Gemini
        if gemini_key:
            try:
                response = requests.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent",
                    params={"key": gemini_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": "test"}]}],
                        "generationConfig": {"maxOutputTokens": 5}
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    results.append("✓ Gemini API: OK")
                else:
                    results.append(f"✗ Gemini API: Error {response.status_code}")
            except Exception as e:
                results.append(f"✗ Gemini API: {str(e)}")
        
        # Test Ollama
        if use_ollama:
            try:
                response = requests.get(f"{ollama_url}/api/tags", timeout=3)
                
                if response.status_code == 200:
                    results.append("✓ Ollama: OK")
                else:
                    results.append(f"✗ Ollama: Error {response.status_code}")
            except Exception as e:
                results.append(f"✗ Ollama: Not running or unreachable")
        
        message = "\n".join(results)
        QMessageBox.information(self, "Test Results", message)
    
    def test_image_providers(self):
        """Test kết nối Image Providers với giao diện đẹp"""
        pexels_key = self.pexels_input.text().strip()
        unsplash_key = self.unsplash_input.text().strip()
        pixabay_key = self.pixabay_input.text().strip()
        
        results = []
        
        # Test Pexels
        if pexels_key:
            try:
                response = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": pexels_key},
                    params={"query": "test", "per_page": 1},
                    timeout=5
                )
                if response.status_code == 200:
                    results.append(("Pexels", "OK", True, "High quality images"))
                else:
                    results.append(("Pexels", f"Error {response.status_code}", False, "API error"))
            except Exception as e:
                results.append(("Pexels", str(e), False, "Connection error"))
        else:
            results.append(("Pexels", "No API key", None, "Optional provider"))
        
        # Test Unsplash
        if unsplash_key:
            try:
                response = requests.get(
                    "https://api.unsplash.com/search/photos",
                    headers={"Authorization": f"Client-ID {unsplash_key}"},
                    params={"query": "test", "per_page": 1},
                    timeout=5
                )
                if response.status_code == 200:
                    results.append(("Unsplash", "OK", True, "Creative commons"))
                else:
                    results.append(("Unsplash", f"Error {response.status_code}", False, "API error"))
            except Exception as e:
                results.append(("Unsplash", str(e), False, "Connection error"))
        else:
            results.append(("Unsplash", "No API key", None, "Optional provider"))
        
        # Test Pixabay
        if pixabay_key:
            try:
                response = requests.get(
                    "https://pixabay.com/api/",
                    params={"key": pixabay_key, "q": "test", "per_page": 3},
                    timeout=5
                )
                if response.status_code == 200:
                    results.append(("Pixabay", "OK", True, "High quality / Animated images"))
                else:
                    results.append(("Pixabay", f"Error {response.status_code}", False, "API error"))
            except Exception as e:
                results.append(("Pixabay", str(e), False, "Connection error"))
        else:
            results.append(("Pixabay", "No API key", None, "Optional provider"))
        
        # Test Openverse (no API key needed)
        try:
            response = requests.get(
                "https://api.openverse.engineering/v1/images",
                params={"q": "test", "page_size": 1},
                timeout=5,
                headers={"User-Agent": "AnkiAI/4.0"}
            )
            if response.status_code == 200:
                results.append(("Openverse", "OK", True, "No API needed"))
            else:
                results.append(("Openverse", f"Error {response.status_code}", False, "Connection failed"))
        except Exception as e:
            results.append(("Openverse", str(e), False, "Connection error"))
        
        # Test Lorem Picsum (no API key needed)
        try:
            response = requests.get("https://picsum.photos/200/300", timeout=3, allow_redirects=False)
            if response.status_code in [200, 301, 302]:
                results.append(("Lorem Picsum", "OK", True, "No API needed"))
            else:
                results.append(("Lorem Picsum", f"Error {response.status_code}", False, "Connection failed"))
        except Exception as e:
            results.append(("Lorem Picsum", str(e), False, "Connection error"))
        
        # Test Library of Congress — use same URL/params/headers as backend (www.loc.gov/search)
        try:
            response = requests.get(
                "https://www.loc.gov/search",
                params={"q": "test", "fo": "json", "fa": "online-format:image"},
                headers={"User-Agent": "AnkiAI-ImageAddon/5.0 (Educational flashcard tool)"},
                timeout=8,
            )
            if response.status_code == 200:
                results.append(("Library of Congress", "OK", True, "Historical images"))
            else:
                results.append(("Library of Congress", f"Error {response.status_code}", False, "Connection failed"))
        except Exception as e:
            results.append(("Library of Congress", str(e), False, "Connection error"))
        
        # Test Wikimedia Commons — use the Action API exactly as the backend does
        try:
            wiki_headers = {
                "User-Agent": "AnkiAI-ImageAddon/5.0 (Educational flashcard tool; contact: addon-user)",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://commons.wikimedia.org/",
            }
            response = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": "tree",
                    "srnamespace": "6",
                    "srlimit": 1,
                    "format": "json",
                    "origin": "*",
                },
                headers=wiki_headers,
                timeout=8,
            )
            if response.status_code == 200:
                data = response.json()
                hits = data.get("query", {}).get("search", [])
                if hits:
                    results.append(("Wikimedia Commons", "OK", True, "Free encyclopedic images"))
                else:
                    results.append(("Wikimedia Commons", "OK (0 results)", True, "Connected but no hits"))
            else:
                results.append(("Wikimedia Commons", f"Error {response.status_code}", False, "API error"))
        except Exception as e:
            results.append(("Wikimedia Commons", str(e), False, "Connection error"))
        
        # Test Met Museum (no API key needed)
        try:
            response = requests.get("https://collectionapi.metmuseum.org/public/collection/v1/search",
                                   params={"q": "test"}, timeout=5)
            if response.status_code == 200:
                results.append(("Met Museum", "OK", True, "Metropolitan Museum art"))
            else:
                results.append(("Met Museum", f"Error {response.status_code}", False, "Connection failed"))
        except Exception as e:
            results.append(("Met Museum", str(e), False, "Connection error"))
        
        # Test Europeana
        europeana_key = self.europeana_input.text().strip() if hasattr(self, 'europeana_input') else ""
        if europeana_key:
            try:
                response = requests.get("https://api.europeana.eu/record/v2/search.json",
                                       params={"wskey": europeana_key, "query": "test"},
                                       timeout=5)
                if response.status_code == 200:
                    results.append(("Europeana", "OK", True, "European cultural heritage"))
                else:
                    results.append(("Europeana", f"Error {response.status_code}", False, "API error"))
            except Exception as e:
                results.append(("Europeana", str(e), False, "Connection error"))
        else:
            results.append(("Europeana", "No API key", None, "Optional provider"))
        
        # Create beautiful HTML dialog
        html = """
        <html>
        <head>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 10px; background: #161625; color: #F0F0F0; }
                .header { font-size: 16px; font-weight: bold; margin-bottom: 15px; color: #14b8a6; }
                .provider { display: flex; align-items: center; padding: 10px; margin: 8px 0; border-radius: 8px; background: #202035; border-left: 4px solid #3F3F3F; }
                .provider.ok { border-left-color: #14b8a6; background: #1a2e2c; }
                .provider.error { border-left-color: #f87171; background: #2a1a1a; }
                .provider.optional { border-left-color: #D4AF37; background: #252218; }
                .icon { font-size: 20px; width: 30px; margin-right: 10px; }
                .info { flex: 1; }
                .name { font-weight: bold; color: #F0F0F0; margin-bottom: 3px; }
                .status { font-size: 12px; color: #A0A0A0; }
                .status.ok { color: #5eead4; font-weight: bold; }
                .status.error { color: #f87171; font-weight: bold; }
                .status.optional { color: #D4AF37; }
                .desc { font-size: 11px; color: #A0A0A0; margin-top: 4px; }
            </style>
        </head>
        <body>
        <div class="header">🔍 Image Provider Status</div>
        """
        
        for name, status, is_ok, desc in results:
            if is_ok:
                icon, css_class = "✅", "ok"
            elif is_ok is False:
                icon, css_class = "❌", "error"
            else:
                icon, css_class = "⊘", "optional"
            
            html += f"""
            <div class="provider {css_class}">
                <div class="icon">{icon}</div>
                <div class="info">
                    <div class="name">{name}</div>
                    <div class="status {css_class}">{status}</div>
                    <div class="desc">{desc}</div>
                </div>
            </div>
            """
        
        html += "</body></html>"
        
        # Show in custom dialog
        dialog = QDialog(self)
        apply_dialog_theme(dialog)
        dialog.setWindowTitle("AnkiAI — Trạng thái nguồn ảnh")
        dialog.setGeometry(100, 100, 520, 420)

        layout = QVBoxLayout()
        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setOpenExternalLinks(False)
        layout.addWidget(browser)
        ok_button = QPushButton("Đóng")
        ok_button.setProperty("primary", True)
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)
        dialog.setLayout(layout)
        dialog.exec()


class ProgressDialog(QDialog):
    """Dialog để hiển thị progress khi thêm ảnh"""
    
    def __init__(self, total_cards: int, parent=None):
        """Khởi tạo ProgressDialog"""
        super().__init__(parent)
        self.total_cards = total_cards
        self.current_card = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.is_cancelled = False
        self.init_ui()
    
    def init_ui(self):
        """Tạo giao diện progress"""
        apply_dialog_theme(self)
        self.setWindowTitle("AnkiAI — Đang thêm ảnh")
        self.setMinimumWidth(520)
        self.setMinimumHeight(280)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(f"Đang xử lý {self.total_cards} thẻ…")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_cards)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Info layout (card current/total)
        info_layout = QHBoxLayout()
        self.info_label = QLabel("Thẻ: 0/0")
        self.info_label.setProperty("muted", True)
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Status message
        self.status_label = QLabel("Khởi tạo…")
        self.status_label.setProperty("muted", True)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Detail message
        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)
        
        # Stats layout
        stats_layout = QHBoxLayout()
        self.success_label = QLabel("Thành công: 0")
        self.success_label.setStyleSheet("color: #5eead4; font-weight: 600;")
        self.skipped_label = QLabel("Bỏ qua: 0")
        self.skipped_label.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.failed_label = QLabel("Thất bại: 0")
        self.failed_label.setStyleSheet("color: #f87171; font-weight: 600;")
        stats_layout.addWidget(self.success_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.skipped_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.failed_label)
        layout.addLayout(stats_layout)
        
        # Cancel button
        self.cancel_button = QPushButton("Dừng batch")
        self.cancel_button.setProperty("danger", True)
        self.cancel_button.clicked.connect(self.cancel)
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
        self._on_cancel_callback = None

    def set_cancel_callback(self, callback: Callable[[], None]):
        self._on_cancel_callback = callback
    
    def update_progress(self, current: int, total: int, status_msg: str, detail_msg: str = ""):
        """Cập nhật progress"""
        self.current_card = current
        self.progress_bar.setValue(current)
        self.info_label.setText(f"Thẻ: {current}/{total}")
        self.status_label.setText(status_msg)
        if detail_msg:
            self.detail_label.setText(detail_msg)
        
        # Update percentage
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setFormat(f"{percentage}%")
        
        # Process events để UI responsive
        from aqt.qt import QApplication
        QApplication.processEvents()
    
    def update_stats(self, successful: int, skipped: int, failed: int):
        """Cập nhật thống kê"""
        self.successful = successful
        self.skipped = skipped
        self.failed = failed
        self.success_label.setText(f"✓ Thành công: {successful}")
        self.skipped_label.setText(f"ℹ Bỏ qua: {skipped}")
        self.failed_label.setText(f"✗ Thất bại: {failed}")
    
    def cancel(self):
        """Hủy bỏ"""
        self.is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Đang dừng…")
        if self._on_cancel_callback:
            self._on_cancel_callback()
    
    def finish(self, success_count: int, skipped_count: int, fail_count: int):
        """Hoàn thành"""
        self.progress_bar.setValue(self.total_cards)
        self.progress_bar.setFormat("100%")
        self.status_label.setText("Hoàn thành")
        self.cancel_button.setText("Đóng")
        self.cancel_button.setProperty("danger", False)
        self.cancel_button.setProperty("primary", True)
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)
        self.update_stats(success_count, skipped_count, fail_count)


def get_note_data(note) -> tuple:
    """
    Trích xuất dữ liệu từ note
    
    Args:
        note: Anki Note object
    
    Returns:
        Tuple (vocabulary, definition)
    """
    try:
        # Thử lấy field phổ biến
        fields = {name: note[name] for name in note.keys()}
        
        # Ưu tiên các tên field tiếng Anh
        vocabulary = (
            fields.get("Front") or
            fields.get("Mặt trước") or
            fields.get("Word") or
            fields.get("Question") or
            list(fields.values())[0] if fields else ""
        )
        
        definition = (
            fields.get("Back") or
            fields.get("Mặt sau") or
            fields.get("Definition") or
            fields.get("Định nghĩa") or
            fields.get("Answer") or
            list(fields.values())[1] if len(fields) > 1 else ""
        )
        
        # Loại bỏ HTML tags
        vocabulary = re.sub(r"<[^>]+>", "", vocabulary).strip()
        definition = re.sub(r"<[^>]+>", "", definition).strip()
        
        return vocabulary, definition
    
    except Exception as e:
        logger.warning(f"Error getting note data: {e}")
        return "", ""
