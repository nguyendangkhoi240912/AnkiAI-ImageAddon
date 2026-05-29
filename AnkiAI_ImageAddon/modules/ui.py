"""
UI Handler Module - Giao diện người dùng & Browser Context Menu
Giai đoạn 1: Tạo menu trong Browser và trích xuất dữ liệu thẻ
"""

from aqt import mw
from aqt.browser import Browser
from aqt.qt import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QWidget, QProgressBar, QLineEdit, QTextBrowser
from typing import List, Optional, Callable
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
    
    def setup_browser_menu(self, browser: Browser, callback_add_images: callable):
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
            action = browser.form.menu_Cards.addAction("AnkiAI: Tự động thêm ảnh bằng AI")
            action.triggered.connect(lambda: callback_add_images(browser))
            logger.info("Menu added to Cards menu")
        except Exception as e1:
            logger.warning(f"Failed to add to Cards menu: {e1}")
            # Thử menu_Notes (Anki 25+)
            try:
                action = browser.form.menu_Notes.addAction("AnkiAI: Tự động thêm ảnh bằng AI")
                action.triggered.connect(lambda: callback_add_images(browser))
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


class FieldSelectionDialog(QDialog):
    """Dialog cho người dùng chọn các field"""
    
    def __init__(self, model_name: str, available_fields: List[str], parent=None):
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
        
        self.init_ui(model_name)
    
    def init_ui(self, model_name: str):
        """Tạo giao diện dialog"""
        self.setWindowTitle(f"Chọn fields - {model_name}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Chọn field từ vựng
        layout.addWidget(QLabel("Chọn field Từ vựng:"))
        vocab_combo = QComboBox()
        vocab_combo.addItems(self.available_fields)
        # Thử tìm field mặc định
        if "Mặt trước" in self.available_fields:
            vocab_combo.setCurrentText("Mặt trước")
        layout.addWidget(vocab_combo)
        
        # Chọn field định nghĩa
        layout.addWidget(QLabel("Chọn field Định nghĩa:"))
        definition_combo = QComboBox()
        definition_combo.addItems(self.available_fields)
        if "Định nghĩa" in self.available_fields:
            definition_combo.setCurrentText("Định nghĩa")
        layout.addWidget(definition_combo)
        
        # ✨ NEW: Chọn field Ví dụ
        layout.addWidget(QLabel("Chọn field Ví dụ (tùy chọn):"))
        examples_combo = QComboBox()
        examples_combo.addItems([""] + self.available_fields)
        if "Ví dụ" in self.available_fields:
            examples_combo.setCurrentText("Ví dụ")
        layout.addWidget(examples_combo)
        
        # Chọn field ảnh
        layout.addWidget(QLabel("Chọn field Ảnh:"))
        image_combo = QComboBox()
        image_combo.addItems(self.available_fields)
        if "Ảnh" in self.available_fields:
            image_combo.setCurrentText("Ảnh")
        layout.addWidget(image_combo)
        
        # Nút OK/Cancel
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Hủy")
        
        ok_button.clicked.connect(lambda: self.accept_with_values(
            vocab_combo.currentText(),
            definition_combo.currentText(),
            examples_combo.currentText(),
            image_combo.currentText()
        ))
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def accept_with_values(self, vocab_field: str, definition_field: str, examples_field: str, image_field: str):
        """Lưu lựa chọn và đóng dialog"""
        self.selected_vocab_field = vocab_field
        self.selected_definition_field = definition_field
        self.selected_examples_field = examples_field
        self.selected_image_field = image_field
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
        """Tạo giao diện config"""
        from aqt.qt import QLineEdit, QCheckBox, QScrollArea
        
        self.setWindowTitle("AnkiAI v5.0 - Cài đặt (Multi-Gemini + 20+ Image/GIF Providers + AI Image Generation)")
        self.setMinimumWidth(650)
        self.setMinimumHeight(850)
        
        main_layout = QVBoxLayout()
        
        # Tạo scroll area để chứa tất cả fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QVBoxLayout()
        
        # ✨ NEW v5.0: Image Generation Mode
        scroll_widget.addWidget(QLabel("🎨 Chế độ hoạt động chính (Image Generation Mode):"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Tìm kiếm ảnh thông thường (Search Mode)", "search")
        self.mode_combo.addItem("Tạo ảnh bằng AI độc nhất (AI Generation Mode - Imagen)", "generate")
        self.mode_combo.addItem("Tự động thông minh (Smart Selection Mode)", "smart")
        self.mode_combo.setToolTip("Chọn cách hoạt động: Tìm kiếm từ các nguồn có sẵn hoặc tự động tạo ảnh bằng AI Imagen 4 Ultra.")
        scroll_widget.addWidget(self.mode_combo)
        
        # AI Providers (v4.2 - Multi-key Gemini)
        scroll_widget.addWidget(QLabel("\n🤖 AI Providers cho Từ khóa & Định nghĩa (cấu hình ít nhất một):"))
        
        # Groq API Key
        scroll_widget.addWidget(QLabel("Groq API Key (⭐ Nên dùng - siêu nhanh, miễn phí):"))
        self.groq_input = QLineEdit()
        self.groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_input.setPlaceholderText("Get from: console.groq.com/keys")
        scroll_widget.addWidget(self.groq_input)
        
        # ✨ Gemini API Keys (v4.2 - 4 keys for multi-key fallback architecture)
        scroll_widget.addWidget(QLabel("\n🔑 Gemini API Keys (Multi-key Architecture - v4.2):"))
        
        scroll_widget.addWidget(QLabel("Gemini API Key #1 (⭐ Keyword Generator - Primary):"))
        self.gemini_input = QLineEdit()
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("Get from: makersuite.google.com/app/apikey (Key #1 - keyword generation)")
        scroll_widget.addWidget(self.gemini_input)
        
        scroll_widget.addWidget(QLabel("Gemini API Key #2 (tuỳ chọn - Backup for Keyword Gen):"))
        self.gemini_backup_input = QLineEdit()
        self.gemini_backup_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_backup_input.setPlaceholderText("Get from: makersuite.google.com/app/apikey (Key #2 - backup)")
        scroll_widget.addWidget(self.gemini_backup_input)
        
        scroll_widget.addWidget(QLabel("Gemini API Key #3 (tuỳ chọn - Backup for Keyword Gen):"))
        self.gemini_keyword_backup_input = QLineEdit()
        self.gemini_keyword_backup_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_keyword_backup_input.setPlaceholderText("Get from: makersuite.google.com/app/apikey (backup for keyword gen)")
        scroll_widget.addWidget(self.gemini_keyword_backup_input)
        
        # Ollama Checkbox
        scroll_widget.addWidget(QLabel("\nOllama (Local backup - hoàn toàn miễn phí):"))
        self.ollama_checkbox = QCheckBox("Sử dụng Ollama local")
        self.ollama_checkbox.setToolTip("Chạy trên máy của bạn, không cần internet. Yêu cầu: ollama pull mistral")
        scroll_widget.addWidget(self.ollama_checkbox)
        
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setText("http://localhost:11434")
        self.ollama_url_input.setPlaceholderText("URL của Ollama server")
        scroll_widget.addWidget(self.ollama_url_input)
        
        # ✨ Image Search Providers (15+ sources - v4.2)
        scroll_widget.addWidget(QLabel("\n📷 Image Search Providers (Cấu hình ít nhất một nếu dùng Search Mode):"))
        
        scroll_widget.addWidget(QLabel("Pexels API Key (⭐ Nên cấu hình - nhanh, chất lượng cao):"))
        self.pexels_input = QLineEdit()
        self.pexels_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pexels_input.setPlaceholderText("Get from: pexels.com/api")
        scroll_widget.addWidget(self.pexels_input)
        
        scroll_widget.addWidget(QLabel("Unsplash API Key (tuỳ chọn):"))
        self.unsplash_input = QLineEdit()
        self.unsplash_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.unsplash_input.setPlaceholderText("Get from: unsplash.com/developers")
        scroll_widget.addWidget(self.unsplash_input)
        
        scroll_widget.addWidget(QLabel("Pixabay API Key (⭐ Khuyến nghị - Miễn phí, chất lượng cao):"))
        self.pixabay_input = QLineEdit()
        self.pixabay_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pixabay_input.setPlaceholderText("Get from: pixabay.com/api")
        scroll_widget.addWidget(self.pixabay_input)
        
        scroll_widget.addWidget(QLabel("Europeana API Key (tuỳ chọn - v4.2):"))
        self.europeana_input = QLineEdit()
        self.europeana_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.europeana_input.setPlaceholderText("Get from: pro.europeana.eu/page/apis")
        scroll_widget.addWidget(self.europeana_input)
        
        # ✨ NEW v5.0: GIF / Animated Image Providers
        scroll_widget.addWidget(QLabel("\n🎬 Animated GIF & Icon Providers (Cấu hình tùy chọn cho ảnh động):"))
        
        scroll_widget.addWidget(QLabel("KLIPY App Key (⭐ Nên dùng cho ảnh động - Free):"))
        self.klipy_input = QLineEdit()
        self.klipy_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.klipy_input.setPlaceholderText("Get from: klipy.ai / api.klipy.ai")
        scroll_widget.addWidget(self.klipy_input)
        
        scroll_widget.addWidget(QLabel("GIPHY API Key (Beta key cho ảnh động):"))
        self.giphy_input = QLineEdit()
        self.giphy_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.giphy_input.setPlaceholderText("Get from: developers.giphy.com")
        scroll_widget.addWidget(self.giphy_input)
        
        scroll_widget.addWidget(QLabel("Tenor API Key (Sẽ hết hạn sau 30/06/2026):"))
        self.tenor_input = QLineEdit()
        self.tenor_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.tenor_input.setPlaceholderText("Get from: Google Cloud Console")
        scroll_widget.addWidget(self.tenor_input)
        
        scroll_widget.addWidget(QLabel("IconScout API Token (Cho Animated Icons):"))
        self.iconscout_input = QLineEdit()
        self.iconscout_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.iconscout_input.setPlaceholderText("Get from: iconscout.com/api")
        scroll_widget.addWidget(self.iconscout_input)
        
        # 🆕 v4.4: Gemini Image Evaluator - 7 API keys with auto-failover
        scroll_widget.addWidget(QLabel("\n🎯 Gemini Image Evaluator (7 API Keys - Auto Failover v4.4):"))
        
        # Enable checkbox
        self.enable_ai_eval_checkbox = QCheckBox("Sử dụng Gemini Vision để đánh giá & chọn ảnh tốt nhất")
        self.enable_ai_eval_checkbox.setToolTip("Gemini sẽ so sánh các ảnh candidate và chọn ảnh phù hợp nhất (kích hoạt khi cấu hình ít nhất 1 API key)")
        self.enable_ai_eval_checkbox.setChecked(True)
        scroll_widget.addWidget(self.enable_ai_eval_checkbox)
        
        # Create 7 input fields for Gemini eval API keys
        self.gemini_eval_inputs = []
        for i in range(1, 8):
            label = QLabel(f"Gemini Eval API Key #{i} (Sẽ dùng làm backup nếu #{i-1} bị khoá):")
            input_field = QLineEdit()
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
            input_field.setPlaceholderText(f"API key #{i} - Leave blank if not needed")
            scroll_widget.addWidget(label)
            scroll_widget.addWidget(input_field)
            self.gemini_eval_inputs.append(input_field)
            
        # 🆕 v5.0: AI Image Generation (Google Imagen 4 Ultra)
        scroll_widget.addWidget(QLabel("\n🔮 AI Image Generation (Google Imagen 4 Ultra):"))
        
        self.enable_imagen_checkbox = QCheckBox("Kích hoạt tự động tạo ảnh bằng AI Imagen 4 Ultra")
        self.enable_imagen_checkbox.setToolTip("Sử dụng Imagen 4 Ultra để tự sinh ảnh độc nhất dựa trên từ vựng")
        scroll_widget.addWidget(self.enable_imagen_checkbox)
        
        scroll_widget.addWidget(QLabel("Imagen API Key (Google AI Studio Key):"))
        self.imagen_api_key_input = QLineEdit()
        self.imagen_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.imagen_api_key_input.setPlaceholderText("Get from: aistudio.google.com")
        scroll_widget.addWidget(self.imagen_api_key_input)
        
        self.enable_gemini_desc_checkbox = QCheckBox("Sử dụng Gemini để tự động viết mô tả ảnh chi tiết (Prompt Guide)")
        self.enable_gemini_desc_checkbox.setToolTip("Gemini sẽ tự động phân tích nghĩa và ví dụ để viết Prompt Guide chi tiết gửi sang Imagen.")
        self.enable_gemini_desc_checkbox.setChecked(True)
        scroll_widget.addWidget(self.enable_gemini_desc_checkbox)
        
        scroll_widget.addWidget(QLabel("Gemini Description API Key (Primary):"))
        self.gemini_desc_input = QLineEdit()
        self.gemini_desc_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_desc_input.setPlaceholderText("Get from: aistudio.google.com")
        scroll_widget.addWidget(self.gemini_desc_input)
        
        scroll_widget.addWidget(QLabel("Gemini Description API Key (Backup 1):"))
        self.gemini_desc_backup1_input = QLineEdit()
        self.gemini_desc_backup1_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_desc_backup1_input.setPlaceholderText("Leave blank if not needed")
        scroll_widget.addWidget(self.gemini_desc_backup1_input)
        
        scroll_widget.addWidget(QLabel("Gemini Description API Key (Backup 2):"))
        self.gemini_desc_backup2_input = QLineEdit()
        self.gemini_desc_backup2_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_desc_backup2_input.setPlaceholderText("Leave blank if not needed")
        scroll_widget.addWidget(self.gemini_desc_backup2_input)
        
        scroll_widget.addWidget(QLabel("Phong cách ảnh mặc định (Default Style):"))
        self.imagen_style_combo = QComboBox()
        self.imagen_style_combo.addItems(["photorealistic", "illustration", "cartoon", "painting", "3d"])
        scroll_widget.addWidget(self.imagen_style_combo)
        
        scroll_widget.addWidget(QLabel("Kích thước ảnh mặc định (Default Size):"))
        self.imagen_size_combo = QComboBox()
        self.imagen_size_combo.addItems(["1024x1024", "512x512", "256x256", "1536x1536"])
        scroll_widget.addWidget(self.imagen_size_combo)
        
        self.imagen_fallback_checkbox = QCheckBox("Tự động chuyển về tìm kiếm (Search Fallback) nếu sinh ảnh lỗi")
        self.imagen_fallback_checkbox.setChecked(True)
        scroll_widget.addWidget(self.imagen_fallback_checkbox)
        
        # ✨ NEW v4.2 Rate Limit Protection
        scroll_widget.addWidget(QLabel("\n⚡ Rate Limit Protection (v4.2):"))
        self.enable_rate_limit_checkbox = QCheckBox("Bật tính năng tự động dừng khi chạm giới hạn API")
        self.enable_rate_limit_checkbox.setToolTip("Nếu API trả về 429/503, hệ thống sẽ tự động dừng 60 giây rồi tiếp tục")
        self.enable_rate_limit_checkbox.setChecked(True)
        scroll_widget.addWidget(self.enable_rate_limit_checkbox)
        
        scroll_widget.addWidget(QLabel("Thời gian tạm dừng (giây - v4.2):"))
        self.rate_limit_pause_input = QLineEdit()
        self.rate_limit_pause_input.setText("60")
        self.rate_limit_pause_input.setPlaceholderText("Default: 60 seconds")
        scroll_widget.addWidget(self.rate_limit_pause_input)
        
        # ✨ NEW v5.1 Skip Existing Images
        scroll_widget.addWidget(QLabel("\n⚙️ Tùy chọn xử lý ảnh (v5.1):"))
        self.skip_existing_images_checkbox = QCheckBox("Tự động bỏ qua các thẻ đã có ảnh sẵn")
        self.skip_existing_images_checkbox.setToolTip("Nếu bật, các thẻ đã có sẵn hình ảnh trong field Ảnh sẽ được tự động bỏ qua để tránh ghi đè.")
        self.skip_existing_images_checkbox.setChecked(True)
        scroll_widget.addWidget(self.skip_existing_images_checkbox)
        
        # Test Buttons
        test_ai_button = QPushButton("🔌 Test AI Connections")
        test_ai_button.clicked.connect(self.test_connection)
        scroll_widget.addWidget(test_ai_button)
        
        test_image_button = QPushButton("🖼️ Test Image Providers")
        test_image_button.clicked.connect(self.test_image_providers)
        scroll_widget.addWidget(test_image_button)
        
        # Set scroll content - FIXED: Simple and clean approach
        scroll_widget.addStretch()
        scroll_container = QVBoxLayout()
        scroll_container.setContentsMargins(0, 0, 0, 0)
        scroll_container.addLayout(scroll_widget)
        
        scroll_inner_widget = QVBoxLayout()
        scroll_inner_widget.setContentsMargins(10, 10, 10, 10)
        scroll_inner_widget.addLayout(scroll_container)
        
        scroll_content_widget = QVBoxLayout()
        scroll_content_widget.setContentsMargins(0, 0, 0, 0)
        scroll_content_widget.addLayout(scroll_inner_widget)
        
        # Create widget for scroll area
        scroll_widget_final = QWidget()
        scroll_widget_final.setLayout(scroll_content_widget)
        
        scroll.setWidget(scroll_widget_final)
        main_layout.addWidget(scroll)
        
        # OK/Cancel
        button_layout = QHBoxLayout()
        ok_button = QPushButton("💾 Lưu")
        cancel_button = QPushButton("❌ Hủy")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
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
        
        # Test Library of Congress (no API key needed)
        try:
            response = requests.get("https://loc.gov/pictures/search/", 
                                   params={"q": "test", "fo": "json"}, timeout=5)
            if response.status_code == 200:
                results.append(("Library of Congress", "OK", True, "Historical images"))
            else:
                results.append(("Library of Congress", f"Error {response.status_code}", False, "Connection failed"))
        except Exception as e:
            results.append(("Library of Congress", str(e), False, "Connection error"))
        
        # Skip Wikimedia Commons test (persistently blocked with 403)
        # The provider still works for actual image search, just blocked in test
        results.append(("Wikimedia Commons", "Skipped", None, "Test blocked by server"))
        
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
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 10px; background: #f5f5f5; }
                .header { font-size: 16px; font-weight: bold; margin-bottom: 15px; color: #333; }
                .provider { display: flex; align-items: center; padding: 10px; margin: 8px 0; border-radius: 8px; background: white; border-left: 4px solid #ddd; }
                .provider.ok { border-left-color: #4CAF50; background: #f1f8f4; }
                .provider.error { border-left-color: #f44336; background: #fef5f5; }
                .provider.optional { border-left-color: #FFC107; background: #fffbf0; }
                .icon { font-size: 20px; width: 30px; margin-right: 10px; }
                .info { flex: 1; }
                .name { font-weight: bold; color: #333; margin-bottom: 3px; }
                .status { font-size: 12px; color: #666; }
                .status.ok { color: #4CAF50; font-weight: bold; }
                .status.error { color: #f44336; font-weight: bold; }
                .status.optional { color: #FF9800; }
                .desc { font-size: 11px; color: #999; margin-top: 4px; }
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
        dialog.setWindowTitle("AnkiAI - Provider Status")
        dialog.setGeometry(100, 100, 500, 400)
        
        layout = QVBoxLayout()
        
        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setOpenExternalLinks(False)
        
        layout.addWidget(browser)
        
        ok_button = QPushButton("OK")
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
        self.setWindowTitle("🖼️ AnkiAI - Đang Thêm Ảnh")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # Tiêu đề
        title_label = QLabel(f"Đang xử lý {self.total_cards} thẻ...")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Progress bar chính
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_cards)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Info layout (card current/total)
        info_layout = QHBoxLayout()
        self.info_label = QLabel("Thẻ: 0/0")
        self.info_label.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Status message
        self.status_label = QLabel("Khởi tạo...")
        self.status_label.setStyleSheet("color: #666666; font-size: 11px; font-style: italic;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Detail message
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("color: #333333; font-size: 12px;")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)
        
        # Stats layout
        stats_layout = QHBoxLayout()
        self.success_label = QLabel("✓ Thành công: 0")
        self.success_label.setStyleSheet("color: green; font-weight: bold;")
        self.skipped_label = QLabel("ℹ Bỏ qua: 0")
        self.skipped_label.setStyleSheet("color: blue; font-weight: bold;")
        self.failed_label = QLabel("✗ Thất bại: 0")
        self.failed_label.setStyleSheet("color: red; font-weight: bold;")
        stats_layout.addWidget(self.success_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.skipped_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.failed_label)
        layout.addLayout(stats_layout)
        
        # Cancel button
        self.cancel_button = QPushButton("❌ Hủy Bỏ")
        self.cancel_button.clicked.connect(self.cancel)
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
    
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
        self.cancel_button.setText("⏳ Đang dừng...")
    
    def finish(self, success_count: int, skipped_count: int, fail_count: int):
        """Hoàn thành"""
        self.progress_bar.setValue(self.total_cards)
        self.progress_bar.setFormat("100%")
        self.status_label.setText("✅ Hoàn thành!")
        self.cancel_button.setText("🎉 Đóng")
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
