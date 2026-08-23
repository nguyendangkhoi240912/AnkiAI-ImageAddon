"""
UI Handler — AnkiAI Premium Futuristic Desktop Interface.

Visual identity:
  - Midnight navy/black backgrounds (#080A10 → #111520)
  - Electric Blue (#00A3FF) primary accent
  - Violet (#8A2BE2) secondary accent
  - Blue→Violet gradient on primary CTA buttons and progress bar
  - Strong white typography hierarchy
  - Layered depth surfaces
  - Restrained glow on interactive elements

All backend logic, public APIs, config keys, and callbacks preserved exactly.
Only the visual presentation has been upgraded.
"""

import logging
import re
import requests
from typing import List, Optional, Callable, Dict, Any

from aqt import mw
from aqt.browser import Browser
from aqt.qt import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from .ui_theme import apply_dialog_theme, get_tokens, is_dark_mode, build_stylesheet
from .ui_motion import fade_in, stagger_in, animate_progress, Motion
from .ui_widgets import (
    header_section,
    settings_section,
    make_settings_card,
    card_header,
    field_row,
    password_field,
    CredentialField,
    credential_field,
    status_badge,
    info_banner,
    section_spacer,
    divider,
    stat_row_widget,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ENTRANCE ANIMATION HELPER
# ============================================================================

def _animate_entrance(dialog: QWidget) -> None:
    """Fade+stagger direct children of a dialog's main layout on first show.

    Runs once per dialog instance (guarded by ``_entrance_done``). Safe no-op
    under reduced-motion config and if any animation step fails. Layout
    spacers (stretch items) yield ``None`` widgets and are skipped.
    """
    if getattr(dialog, "_entrance_done", False):
        return
    dialog._entrance_done = True
    try:
        lay = dialog.layout()
        if lay is None:
            return
        children = []
        for i in range(lay.count()):
            item = lay.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                children.append(w)
                continue
            # One level deeper: button rows added as sub-layouts
            sub = item.layout()
            if sub is not None:
                for j in range(sub.count()):
                    sw = sub.itemAt(j)
                    if sw is not None and sw.widget() is not None:
                        children.append(sw.widget())
        if not children:
            return
        stagger_in(children, duration=Motion.ENTER, delay_step=Motion.STAGGER)
    except Exception:
        logger.warning("Entrance animation skipped", exc_info=True)


# ============================================================================
# 1. BROWSER MENU MANAGER
# ============================================================================

class BrowserMenuManager:
    """Manages AnkiAI actions in Anki Browser menus."""

    def __init__(self):
        self.browser: Optional[Browser] = None

    def setup_browser_menu(
        self,
        browser: Browser,
        callback_add_images: Callable[[Browser], None],
        callback_resume_batch: Optional[Callable[[Browser], None]] = None,
    ):
        self.browser = browser

        try:
            action = browser.form.menu_Cards.addAction("AnkiAI: Tự động thêm ảnh bằng AI…")
            action.triggered.connect(lambda: callback_add_images(browser))
            if callback_resume_batch:
                resume = browser.form.menu_Cards.addAction("AnkiAI: Tiếp tục batch đã dừng…")
                resume.triggered.connect(lambda: callback_resume_batch(browser))
            return
        except Exception as e1:
            logger.debug(f"Could not attach to Cards menu: {e1}")

        try:
            action = browser.form.menu_Notes.addAction("AnkiAI: Tự động thêm ảnh bằng AI…")
            action.triggered.connect(lambda: callback_add_images(browser))
            if callback_resume_batch:
                resume = browser.form.menu_Notes.addAction("AnkiAI: Tiếp tục batch đã dừng…")
                resume.triggered.connect(lambda: callback_resume_batch(browser))
            return
        except Exception as e2:
            logger.debug(f"Could not attach to Notes menu: {e2}")

        try:
            action = browser.menuBar().addAction("AnkiAI: Tự động thêm ảnh bằng AI…")
            action.triggered.connect(lambda: callback_add_images(browser))
        except Exception as e3:
            logger.error(f"Error setting up browser menu fallback: {e3}")

    def get_selected_note_ids(self, browser: Browser) -> List[int]:
        try:
            selected_cids = browser.selected_cards()
            if not selected_cids:
                return []
            note_ids = set()
            for cid in selected_cids:
                card = mw.col.get_card(cid)
                note_ids.add(card.nid)
            return list(note_ids)
        except Exception as e:
            logger.warning(f"Error getting selected note IDs: {e}")
            return []

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self.browser, title, message)

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self.browser, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self.browser, title, message)

    def show_question(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(self.browser, title, message)
        return reply == QMessageBox.StandardButton.Yes


# ============================================================================
# 2. BATCH OPTIONS DIALOG
# ============================================================================

class BatchOptionsDialog(QDialog):
    """
    Batch processing configuration console.

    Communicates selected note count and batch limits
    with a premium technical-control-panel aesthetic.
    """

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
        self.pending_count = pending_count

        apply_dialog_theme(self)
        self.setWindowTitle("AnkiAI — Batch Processing")
        self.setMinimumWidth(480)
        self.setMaximumWidth(560)
        self._init_ui(selected_count, default_max, pending_count)

    def _init_ui(self, selected_count: int, default_max: int, pending_count: int):
        tokens = get_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        # Header
        layout.addWidget(header_section(
            title="Batch Processing",
            subtitle="Cấu hình giới hạn thẻ để kiểm soát tốc độ xử lý và bảo vệ hạn mức API.",
            icon="⚡"
        ))

        # ── Selected notes count + batch limit ──────────────────────────
        count_card, c_layout = settings_section()
        c_layout.setSpacing(14)

        inner = QHBoxLayout()
        inner.setSpacing(20)

        # Count display block
        count_block = QWidget()
        count_block.setStyleSheet(
            f"QWidget {{ background-color: {tokens['bg_surface']}; "
            f"border: 1px solid {tokens['border_accent']}; border-radius: 12px; }}"
        )
        count_block_layout = QVBoxLayout(count_block)
        count_block_layout.setContentsMargins(20, 14, 20, 14)
        count_block_layout.setSpacing(2)

        num_lbl = QLabel(str(selected_count))
        num_lbl.setStyleSheet(
            f"font-size: 38px; font-weight: 800; color: {tokens['accent']}; "
            f"background: transparent; letter-spacing: -2px; border: none;"
        )
        count_block_layout.addWidget(num_lbl)

        type_lbl = QLabel("thẻ đã chọn")
        type_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {tokens['text_low']}; "
            f"background: transparent; letter-spacing: 0.8px; border: none;"
        )
        count_block_layout.addWidget(type_lbl)

        inner.addWidget(count_block)

        # Limit controls
        ctrl = QVBoxLayout()
        ctrl.setSpacing(8)

        ctrl.addWidget(field_row(
            "Số thẻ tối đa mỗi lần chạy",
            "0 = xử lý toàn bộ · 50–100 thẻ/lần giúp kiểm soát rate limit tốt hơn"
        ))

        self.max_spin = QSpinBox()
        self.max_spin.setRange(0, max(selected_count, 1))
        self.max_spin.setValue(
            min(default_max, selected_count) if default_max > 0 else selected_count
        )
        self.max_spin.setToolTip("0 = xử lý toàn bộ thẻ đã chọn")
        self.max_spin.setFixedWidth(110)
        ctrl.addWidget(self.max_spin)
        ctrl.addStretch()

        inner.addLayout(ctrl, stretch=1)
        c_layout.addLayout(inner)
        layout.addWidget(count_card)

        # ── Pending batch card ───────────────────────────────────────────
        if pending_count > 0:
            pending_card, p_layout = settings_section(
                title="Batch tạm dừng",
                icon="⏸"
            )
            p_row = QHBoxLayout()
            p_row.setSpacing(16)

            pend_num = QLabel(str(pending_count))
            pend_num.setStyleSheet(
                f"font-size: 28px; font-weight: 800; color: {tokens['warn']}; "
                f"background: transparent; border: none;"
            )
            p_row.addWidget(pend_num)

            p_v = QVBoxLayout()
            p_v.setSpacing(3)
            p_lbl = QLabel("thẻ đang chờ từ lần chạy trước")
            p_lbl.setProperty("fieldLabel", True)
            p_v.addWidget(p_lbl)
            p_h = QLabel("Tiếp tục batch cũ thay vì bắt đầu batch mới")
            p_h.setProperty("hint", True)
            p_v.addWidget(p_h)
            p_row.addLayout(p_v, stretch=1)

            self.pending_btn = QPushButton(f"▶  Tiếp tục ({pending_count} thẻ)")
            self.pending_btn.setStyleSheet(
                f"QPushButton {{ background-color: {tokens['warn_dim']}; "
                f"color: {tokens['warn']}; border: 1px solid {tokens['warn']}; "
                f"border-radius: 8px; font-weight: 700; padding: 8px 18px; }}"
                f"QPushButton:hover {{ background-color: {tokens['warn']}; color: #FFFFFF; }}"
            )
            self.pending_btn.clicked.connect(self._accept_pending)
            p_row.addWidget(self.pending_btn)

            p_layout.addLayout(p_row)
            layout.addWidget(pending_card)

        # ── Action buttons ───────────────────────────────────────────────
        layout.addSpacing(4)
        btn_row = QHBoxLayout()

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        ok_btn = QPushButton("▶  Bắt đầu xử lý")
        ok_btn.setProperty("primary", True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._accept_normal)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _accept_normal(self):
        self.use_pending = False
        self.max_notes = self.max_spin.value()
        self.accept()

    def _accept_pending(self):
        self.use_pending = True
        self.accept()

    def showEvent(self, event):
        """Staggered entrance animation on first display."""
        super().showEvent(event)
        _animate_entrance(self)


# ============================================================================
# 3. FIELD SELECTION DIALOG
# ============================================================================

class FieldSelectionDialog(QDialog):
    """
    Note field mapping dialog.

    Preserves all existing field mapping functionality.
    Redesigned for premium technical-desktop visual language.
    """

    def __init__(
        self,
        model_name: str,
        available_fields: List[str],
        parent=None,
        initial: Optional[Dict[str, str]] = None,
    ):
        super().__init__(parent)
        self.available_fields = available_fields
        self.selected_vocab_field = None
        self.selected_definition_field = None
        self.selected_examples_field = None
        self.selected_image_field = None
        self.save_as_preset = False
        self._initial = initial or {}

        self.init_ui(model_name)

    def init_ui(self, model_name: str):
        tokens = get_tokens()
        apply_dialog_theme(self)
        self.setWindowTitle(f"AnkiAI — Khớp trường · {model_name}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        # Header
        layout.addWidget(header_section(
            title="Chọn trường Note",
            subtitle=f"Xác định vai trò của từng trường trong note type «{model_name}».",
            icon="↔"
        ))

        # ── Mapping card ─────────────────────────────────────────────────
        card, card_layout = settings_section(title="Ánh xạ trường", icon="⚙")
        card_layout.setSpacing(8)

        def _make_combo(fields, initial_key, fallbacks):
            c = QComboBox()
            c.addItems(fields)
            val = self._initial.get(initial_key, "")
            if val and val in fields:
                c.setCurrentText(val)
            else:
                for fb in fallbacks:
                    if fb in fields:
                        c.setCurrentText(fb)
                        break
            return c

        def _mapping_row(lbl_text, hint_text, badge, key, fallbacks, optional_prefix=None):
            """Horizontal label + combo mapping row."""
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(16)

            label_block = field_row(lbl_text, hint_text, badge)
            label_block.setFixedWidth(220)
            row_layout.addWidget(label_block)

            if optional_prefix:
                combo = QComboBox()
                combo.addItem(optional_prefix)
                combo.addItems(self.available_fields)
                val = self._initial.get(key, "")
                if val and val in self.available_fields:
                    combo.setCurrentText(val)
                else:
                    for fb in fallbacks:
                        if fb in self.available_fields:
                            combo.setCurrentText(fb)
                            break
            else:
                combo = _make_combo(self.available_fields, key, fallbacks)

            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row_layout.addWidget(combo)
            card_layout.addWidget(row)
            return combo

        self.vocab_combo = _mapping_row(
            "Từ vựng", "Từ/cụm từ cần tìm ảnh",
            "priority", "vocabulary_field",
            ["Mặt trước", "Front", "Word", "Vocab", "Question"]
        )
        card_layout.addWidget(divider())

        self.definition_combo = _mapping_row(
            "Định nghĩa", "Cung cấp ngữ cảnh cho AI",
            "priority", "definition_field",
            ["Định nghĩa", "Definition", "Back", "Mặt sau", "Meaning"]
        )
        card_layout.addWidget(divider())

        self.examples_combo = _mapping_row(
            "Ví dụ", "Giúp AI hiểu ngữ cảnh câu (tùy chọn)",
            "optional", "examples_field",
            ["Ví dụ", "Example"],
            optional_prefix="(Không dùng)"
        )
        card_layout.addWidget(divider())

        self.image_combo = _mapping_row(
            "Trường ảnh", "Nơi hình ảnh được chèn vào",
            "priority", "image_field",
            ["Ảnh", "Image", "Picture", "Illustration", "Photo"]
        )

        layout.addWidget(card)

        # ── Preset option ────────────────────────────────────────────────
        self.remember_checkbox = QCheckBox(
            "Lưu cài đặt này cho note type — tự động áp dụng lần sau"
        )
        self.remember_checkbox.setChecked(True)
        layout.addWidget(self.remember_checkbox)

        # ── Buttons ──────────────────────────────────────────────────────
        layout.addSpacing(4)
        btn_row = QHBoxLayout()

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        ok_btn = QPushButton("Tiếp tục  →")
        ok_btn.setProperty("primary", True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok_clicked)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _on_ok_clicked(self):
        ex_text = self.examples_combo.currentText()
        if ex_text == "(Không dùng)":
            ex_text = ""
        self.accept_with_values(
            self.vocab_combo.currentText(),
            self.definition_combo.currentText(),
            ex_text,
            self.image_combo.currentText(),
        )

    def accept_with_values(
        self,
        vocab_field: str,
        definition_field: str,
        examples_field: str,
        image_field: str,
    ):
        self.selected_vocab_field = vocab_field
        self.selected_definition_field = definition_field
        self.selected_examples_field = examples_field
        self.selected_image_field = image_field
        self.save_as_preset = self.remember_checkbox.isChecked()
        self.accept()

    def showEvent(self, event):
        """Staggered entrance animation on first display."""
        super().showEvent(event)
        _animate_entrance(self)


# ============================================================================
# 4. CONFIGURATION DIALOG
# ============================================================================

class ConfigDialog(QDialog):
    """
    AnkiAI Settings — Premium AI Control Center.

    Four-tab layout. All config keys and logic preserved exactly.
    Presentation elevated with electric-blue / violet visual language.
    """

    def __init__(self, parent=None, existing_config=None):
        super().__init__(parent)
        self.config_values = {}
        self.existing_config = existing_config or {}
        self.init_ui()
        self.load_existing_config()

    def init_ui(self):
        tokens = get_tokens()
        apply_dialog_theme(self)
        self.setWindowTitle("AnkiAI — Settings")
        self.setMinimumWidth(740)
        self.setMinimumHeight(700)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 22)
        main_layout.setSpacing(16)

        main_layout.addWidget(header_section(
            title="AnkiAI Settings",
            subtitle="Cấu hình AI providers, nguồn hình ảnh, và tùy chọn nâng cao.",
            icon="⚙"
        ))

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        self._init_general_tab()
        self._init_ai_providers_tab()
        self._init_image_sources_tab()
        self._init_advanced_tab()

        # Footer
        btn_row = QHBoxLayout()

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        save_btn = QPushButton("💾  Lưu cấu hình")
        save_btn.setProperty("primary", True)
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        main_layout.addLayout(btn_row)

    def showEvent(self, event):
        """Staggered entrance animation on first display."""
        super().showEvent(event)
        _animate_entrance(self)

    # ── TAB 1 — GENERAL ─────────────────────────────────────────────────────
    def _init_general_tab(self):
        tokens = get_tokens()
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Mode
        card_mode, c_layout = settings_section(
            title="Chế độ lấy ảnh",
            subtitle="Cách addon tìm hoặc tạo hình ảnh cho từng flashcard.",
            icon="🎨"
        )
        c_layout.addWidget(field_row("Chế độ xử lý"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔍  Tìm kiếm  —  Search Providers (Nhanh & Đa dạng)", "search")
        self.mode_combo.addItem("✨  Tạo ảnh AI  —  Google Imagen (Độc nhất & Chuẩn ngữ cảnh)", "generate")
        self.mode_combo.addItem("🧠  Thông minh  —  AI trước, fallback tìm kiếm", "smart")
        c_layout.addWidget(self.mode_combo)
        layout.addWidget(card_mode)

        # Rules
        card_rules, r_layout = settings_section(
            title="Quy tắc xử lý",
            subtitle="Kiểm soát hành vi tự động và bảo vệ dữ liệu.",
            icon="📋"
        )

        self.skip_existing_images_checkbox = QCheckBox(
            "Bỏ qua thẻ đã có ảnh trong trường đích  (Khuyến nghị)"
        )
        self.skip_existing_images_checkbox.setChecked(True)
        r_layout.addWidget(self.skip_existing_images_checkbox)

        self.enable_rate_limit_checkbox = QCheckBox(
            "Tự động tạm dừng khi gặp Rate Limit (lỗi 429)"
        )
        self.enable_rate_limit_checkbox.setChecked(True)
        r_layout.addWidget(self.enable_rate_limit_checkbox)

        pause_row = QHBoxLayout()
        pause_row.setSpacing(12)
        pause_lbl = QLabel("Thời gian tạm dừng an toàn (giây):")
        pause_lbl.setProperty("fieldLabel", True)
        pause_row.addWidget(pause_lbl)
        self.rate_limit_pause_input = QLineEdit("60")
        self.rate_limit_pause_input.setFixedWidth(90)
        pause_row.addWidget(self.rate_limit_pause_input)
        pause_row.addStretch()
        r_layout.addLayout(pause_row)

        layout.addWidget(card_rules)
        layout.addStretch()

        self.tabs.addTab(tab, "⚡  Chung")

    # ── TAB 2 — AI PROVIDERS ────────────────────────────────────────────────
    def _init_ai_providers_tab(self):
        tokens = get_tokens()
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        layout.addWidget(info_banner(
            "Cần tối thiểu 1 AI provider (Groq, Gemini, hoặc Ollama) để phân tích từ khóa và tìm kiếm ảnh.",
            state="info"
        ))

        # Groq
        card_groq, g_layout = settings_section(title="Groq  ·  Miễn phí & Siêu nhanh", icon="⚡")
        g_layout.addWidget(field_row(
            "API Key", "Lấy key miễn phí tại console.groq.com/keys",
            badge="recommended"
        ))
        self.groq_input = credential_field("gsk_…")
        g_layout.addWidget(self.groq_input)
        layout.addWidget(card_groq)

        # Gemini
        card_gemini, gm_layout = settings_section(title="Google Gemini AI", icon="🤖")
        gm_layout.addWidget(field_row(
            "API Key #1  —  Chính", "aistudio.google.com/apikey",
            badge="priority"
        ))
        self.gemini_input = credential_field("AIzaSy…")
        gm_layout.addWidget(self.gemini_input)

        gm_layout.addWidget(divider())
        gm_layout.addWidget(field_row(
            "API Key #2  —  Dự phòng", "Tự động kích hoạt khi Key #1 vượt hạn mức",
            badge="optional"
        ))
        self.gemini_backup_input = credential_field("Key dự phòng 1")
        gm_layout.addWidget(self.gemini_backup_input)

        gm_layout.addWidget(divider())
        gm_layout.addWidget(field_row(
            "API Key #3  —  Dự phòng 2", "Dự phòng phụ cho từ khóa",
            badge="optional"
        ))
        self.gemini_keyword_backup_input = credential_field("Key dự phòng 2")
        gm_layout.addWidget(self.gemini_keyword_backup_input)
        layout.addWidget(card_gemini)

        # Ollama
        card_ollama, o_layout = settings_section(title="Ollama  ·  AI cục bộ (Offline)", icon="💻")
        self.ollama_checkbox = QCheckBox("Sử dụng Ollama server cục bộ  (không cần internet)")
        o_layout.addWidget(self.ollama_checkbox)
        o_layout.addWidget(field_row("Server URL", "Mặc định: http://localhost:11434"))
        self.ollama_url_input = QLineEdit("http://localhost:11434")
        o_layout.addWidget(self.ollama_url_input)
        layout.addWidget(card_ollama)

        test_btn = QPushButton("🔍  Kiểm tra kết nối AI")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)

        layout.addStretch()
        scroll.setWidget(body)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "🤖  AI Providers")

    # ── TAB 3 — IMAGE SOURCES ────────────────────────────────────────────────
    def _init_image_sources_tab(self):
        tokens = get_tokens()
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Stock photos
        card_photo, p_layout = settings_section(
            title="Ảnh Stock & Flashcard",
            subtitle="APIs tìm kiếm ảnh chất lượng cao.",
            icon="📷"
        )
        _photo = [
            ("Pexels",    "pexels.com/api",             "recommended", "pexels_input",    "Pexels API key"),
            ("Pixabay",   "pixabay.com/api",             "recommended", "pixabay_input",   "Pixabay API key"),
            ("Unsplash",  "unsplash.com/developers",    "optional",    "unsplash_input",  "Unsplash Access Key"),
            ("Europeana", "pro.europeana.eu",            "optional",    "europeana_input", "Europeana API key"),
        ]
        first = True
        for name, hint, badge, attr, placeholder in _photo:
            if not first:
                p_layout.addWidget(divider())
            first = False
            p_layout.addWidget(field_row(name, hint, badge=badge))
            field = credential_field(placeholder)
            setattr(self, attr, field)
            p_layout.addWidget(field)
        layout.addWidget(card_photo)

        # GIFs
        card_gif, g_layout = settings_section(
            title="GIF & Ảnh động",
            subtitle="Thêm sinh động cho từ vựng hành động và cảm xúc.",
            icon="🎬"
        )
        _gif = [
            ("KLIPY",     "klipy.io/developers",         "recommended", "klipy_input",     "Klipy App Key"),
            ("GIPHY",     "developers.giphy.com",         "optional",    "giphy_input",     "GIPHY API Key"),
            ("IconScout", "iconscout.com/api (Icons & Vectors)", "optional", "iconscout_input", "IconScout Token"),
        ]
        first = True
        for name, hint, badge, attr, placeholder in _gif:
            if not first:
                g_layout.addWidget(divider())
            first = False
            g_layout.addWidget(field_row(name, hint, badge=badge))
            field = credential_field(placeholder)
            setattr(self, attr, field)
            g_layout.addWidget(field)
        layout.addWidget(card_gif)

        # 🆕 v6.1: New providers section
        card_new, n_layout = settings_section(
            title="Nguồn ảnh mới (v6.1)",
            subtitle="21 nguồn ảnh mới: Wikipedia, Wikidata, Smithsonian, Iconify, Mermaid, QuickChart, Pollinations AI, v.v.",
            icon="🆕"
        )
        
        # Smithsonian (optional key for higher rate limit)
        n_layout.addWidget(field_row("Smithsonian Open Access", "api.si.edu — Optional key for higher rate limit", badge="optional"))
        self.smithsonian_input = credential_field("Smithsonian API Key (optional)")
        n_layout.addWidget(self.smithsonian_input)
        n_layout.addWidget(divider())
        
        # Noun Project (OAuth2 - required for full access)
        n_layout.addWidget(field_row("Noun Project", "thenounproject.com — OAuth2 Client ID & Secret", badge="recommended"))
        np_row = QHBoxLayout()
        np_row.setSpacing(10)
        self.noun_project_id_input = credential_field("Client ID")
        self.noun_project_secret_input = credential_field("Client Secret")
        np_row.addWidget(self.noun_project_id_input)
        np_row.addWidget(self.noun_project_secret_input)
        n_layout.addLayout(np_row)
        n_layout.addWidget(divider())
        
        # HuggingFace (required for AI generation)
        n_layout.addWidget(field_row("HuggingFace Inference", "huggingface.co — Required for AI image generation", badge="recommended"))
        self.huggingface_input = credential_field("HuggingFace API Token")
        n_layout.addWidget(self.huggingface_input)
        n_layout.addWidget(divider())
        
        # Flickr (already exists in stock photos section, but mentioned in new providers)
        n_layout.addWidget(field_row("Flickr CC-only", "flickr.com — Already configured in Stock Photos section", badge="info"))
        # Note: Flickr key is already in the stock photos section, so we just show info
        
        layout.addWidget(card_new)

        test_btn = QPushButton("🔍  Kiểm tra tất cả nguồn ảnh")
        test_btn.clicked.connect(self.test_image_providers)
        layout.addWidget(test_btn)

        layout.addStretch()
        scroll.setWidget(body)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "🖼  Nguồn ảnh")

    # ── TAB 4 — ADVANCED ────────────────────────────────────────────────────
    def _init_advanced_tab(self):
        tokens = get_tokens()
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Imagen
        card_imagen, im_layout = settings_section(
            title="Google Imagen  ·  AI Image Generation",
            subtitle="Tạo ảnh minh họa độc quyền cho từng flashcard.",
            icon="✨"
        )
        self.enable_imagen_checkbox = QCheckBox("Bật tạo ảnh bằng Imagen")
        im_layout.addWidget(self.enable_imagen_checkbox)

        im_layout.addWidget(field_row("Imagen API Key", "Google AI Studio Key với quyền Imagen", badge="priority"))
        self.imagen_api_key_input = credential_field("AIzaSy…")
        im_layout.addWidget(self.imagen_api_key_input)

        im_layout.addWidget(divider())
        self.enable_gemini_desc_checkbox = QCheckBox(
            "Gemini mô tả chi tiết ảnh trước khi tạo (Prompt Enhancer)"
        )
        self.enable_gemini_desc_checkbox.setChecked(True)
        im_layout.addWidget(self.enable_gemini_desc_checkbox)

        im_layout.addWidget(field_row("Gemini mô tả  —  Key chính", badge="priority"))
        self.gemini_desc_input = credential_field("Key mô tả chính")
        im_layout.addWidget(self.gemini_desc_input)

        im_layout.addWidget(field_row("Gemini mô tả  —  Backup 1", badge="optional"))
        self.gemini_desc_backup1_input = credential_field("Backup 1")
        im_layout.addWidget(self.gemini_desc_backup1_input)

        im_layout.addWidget(field_row("Gemini mô tả  —  Backup 2", badge="optional"))
        self.gemini_desc_backup2_input = credential_field("Backup 2")
        im_layout.addWidget(self.gemini_desc_backup2_input)

        im_layout.addWidget(divider())

        style_row = QHBoxLayout()
        style_row.setSpacing(14)
        s_lbl = QLabel("Phong cách:")
        s_lbl.setProperty("fieldLabel", True)
        style_row.addWidget(s_lbl)
        self.imagen_style_combo = QComboBox()
        self.imagen_style_combo.addItems(["photorealistic", "illustration", "cartoon", "painting", "3d"])
        style_row.addWidget(self.imagen_style_combo)
        sz_lbl = QLabel("Kích thước:")
        sz_lbl.setProperty("fieldLabel", True)
        style_row.addWidget(sz_lbl)
        self.imagen_size_combo = QComboBox()
        self.imagen_size_combo.addItems(["1024x1024", "512x512", "256x256", "1536x1536"])
        style_row.addWidget(self.imagen_size_combo)
        style_row.addStretch()
        im_layout.addLayout(style_row)

        self.imagen_fallback_checkbox = QCheckBox(
            "Tự động fallback sang tìm kiếm nếu Imagen lỗi hoặc hết hạn mức"
        )
        self.imagen_fallback_checkbox.setChecked(True)
        im_layout.addWidget(self.imagen_fallback_checkbox)
        layout.addWidget(card_imagen)

        # Vision Evaluation
        card_eval, ev_layout = settings_section(
            title="Gemini Vision  ·  AI Image Evaluation",
            subtitle="AI phân tích ứng viên ảnh và chọn tấm sát nghĩa nhất.",
            icon="👁"
        )
        self.enable_ai_eval_checkbox = QCheckBox("Bật Gemini Vision Evaluation")
        self.enable_ai_eval_checkbox.setChecked(True)
        ev_layout.addWidget(self.enable_ai_eval_checkbox)

        self.gemini_eval_inputs = []
        _hints = [
            "Key đầu tiên dùng đánh giá thị giác",
            "Dự phòng #1", "Dự phòng #2", "Dự phòng #3",
            "Dự phòng #4", "Dự phòng #5", "Dự phòng #6",
        ]
        for i in range(1, 8):
            ev_layout.addWidget(divider())
            badge = "priority" if i == 1 else "optional"
            ev_layout.addWidget(field_row(f"Eval Key #{i}", _hints[i - 1], badge=badge))
            inp = credential_field(f"Key #{i}")
            ev_layout.addWidget(inp)
            self.gemini_eval_inputs.append(inp)
        layout.addWidget(card_eval)

        # ── Pipeline & Cache (GĐ5) ──────────────────────────────────────
        card_pipe, pc_layout = settings_section(
            title="Pipeline  ·  Cache  ·  Telemetry",
            subtitle="Cấu hình luồng xử lý, cache SQLite, và đo lường.",
            icon="🔧"
        )

        pc_layout.addWidget(field_row("CLIP tier"))
        self.clip_tier_combo = QComboBox()
        self.clip_tier_combo.addItem("Tự động (khuyên dùng)", "auto")
        self.clip_tier_combo.addItem("Đầy đủ (ONNX fp16/fp32)", "full")
        self.clip_tier_combo.addItem("Lượng tử hoá (INT8)", "quantized")
        self.clip_tier_combo.addItem("Heuristic thuần (không ONNX)", "heuristic")
        pc_layout.addWidget(self.clip_tier_combo)

        self.strict_accuracy_checkbox = QCheckBox(
            "Chế độ chính xác tuyệt đối — không gắn ảnh chưa xác thực (⚠ unverified)"
        )
        pc_layout.addWidget(self.strict_accuracy_checkbox)

        self.idle_prefetch_checkbox = QCheckBox(
            "Tận dụng thời gian rảnh để xử lý trước (idle prefetch)"
        )
        self.idle_prefetch_checkbox.setChecked(True)
        pc_layout.addWidget(self.idle_prefetch_checkbox)

        prefetch_row = QHBoxLayout()
        prefetch_row.setSpacing(12)
        pf_lbl = QLabel("Số thẻ xử lý trước mỗi lần rảnh:")
        pf_lbl.setProperty("fieldLabel", True)
        prefetch_row.addWidget(pf_lbl)
        self.idle_prefetch_batch_spin = QSpinBox()
        self.idle_prefetch_batch_spin.setRange(1, 100)
        self.idle_prefetch_batch_spin.setValue(20)
        self.idle_prefetch_batch_spin.setFixedWidth(80)
        prefetch_row.addWidget(self.idle_prefetch_batch_spin)
        prefetch_row.addStretch()
        pc_layout.addLayout(prefetch_row)

        self.url_only_mode_checkbox = QCheckBox(
            "Chỉ dùng URL (không tải ảnh về — cần mạng khi học)"
        )
        pc_layout.addWidget(self.url_only_mode_checkbox)

        self.telemetry_checkbox = QCheckBox(
            "Ghi đo lường cục bộ (latency, CLIP score, QC rounds)"
        )
        self.telemetry_checkbox.setChecked(True)
        pc_layout.addWidget(self.telemetry_checkbox)

        layout.addWidget(card_pipe)

        layout.addStretch()
        scroll.setWidget(body)
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "⚙  Nâng cao")

    # ── CONFIG LOAD / SAVE ───────────────────────────────────────────────────
    def load_existing_config(self):
        try:
            if not self.existing_config:
                return
            self.groq_input.setText(self.existing_config.get("groq_api_key", ""))
            self.gemini_input.setText(self.existing_config.get("gemini_api_key", ""))
            self.gemini_backup_input.setText(self.existing_config.get("gemini_backup_api_key", ""))
            self.gemini_keyword_backup_input.setText(self.existing_config.get("gemini_keyword_api_key_backup", ""))
            self.ollama_checkbox.setChecked(bool(self.existing_config.get("use_ollama", False)))
            self.ollama_url_input.setText(self.existing_config.get("ollama_url", "http://localhost:11434"))
            self.unsplash_input.setText(self.existing_config.get("unsplash_api_key", ""))
            self.pexels_input.setText(self.existing_config.get("pexels_api_key", ""))
            self.pixabay_input.setText(self.existing_config.get("pixabay_api_key", ""))
            self.europeana_input.setText(self.existing_config.get("europeana_api_key", ""))
            self.klipy_input.setText(self.existing_config.get("klipy_app_key", ""))
            self.giphy_input.setText(self.existing_config.get("giphy_api_key", ""))
            self.iconscout_input.setText(self.existing_config.get("iconscout_api_token", ""))
            self.smithsonian_input.setText(self.existing_config.get("smithsonian_api_key", ""))
            self.huggingface_input.setText(self.existing_config.get("huggingface_api_token", ""))
            self.noun_project_id_input.setText(self.existing_config.get("noun_project_api_key", ""))
            self.noun_project_secret_input.setText(self.existing_config.get("noun_project_api_secret", ""))
            self.enable_ai_eval_checkbox.setChecked(bool(self.existing_config.get("enable_ai_evaluation", True)))
            for i in range(1, 8):
                key = self.existing_config.get(f"gemini_eval_api_key_{i}", "")
                if i - 1 < len(self.gemini_eval_inputs):
                    self.gemini_eval_inputs[i - 1].setText(key)
            self.enable_rate_limit_checkbox.setChecked(bool(self.existing_config.get("enable_rate_limit_protection", True)))
            self.rate_limit_pause_input.setText(str(self.existing_config.get("rate_limit_pause_duration", 60)))
            mode = self.existing_config.get("image_generation_mode", "search")
            idx = self.mode_combo.findData(mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            self.skip_existing_images_checkbox.setChecked(bool(self.existing_config.get("skip_existing_images", True)))
            self.enable_imagen_checkbox.setChecked(bool(self.existing_config.get("imagen_enabled", False)))
            self.imagen_api_key_input.setText(self.existing_config.get("imagen_api_key", ""))
            self.enable_gemini_desc_checkbox.setChecked(bool(self.existing_config.get("enable_gemini_image_description", True)))
            self.gemini_desc_input.setText(self.existing_config.get("gemini_image_description_api_key", ""))
            self.gemini_desc_backup1_input.setText(self.existing_config.get("gemini_image_description_api_key_backup_1", ""))
            self.gemini_desc_backup2_input.setText(self.existing_config.get("gemini_image_description_api_key_backup_2", ""))
            self.imagen_style_combo.setCurrentText(self.existing_config.get("imagen_default_style", "photorealistic"))
            self.imagen_size_combo.setCurrentText(self.existing_config.get("imagen_default_size", "1024x1024"))
            self.imagen_fallback_checkbox.setChecked(bool(self.existing_config.get("imagen_fallback_to_search_providers", True)))
            # GĐ5 Pipeline & Cache settings
            clip_tier = self.existing_config.get("clip_tier", "auto")
            ct_idx = self.clip_tier_combo.findData(clip_tier)
            if ct_idx >= 0:
                self.clip_tier_combo.setCurrentIndex(ct_idx)
            self.strict_accuracy_checkbox.setChecked(bool(self.existing_config.get("strict_accuracy_mode", False)))
            self.idle_prefetch_checkbox.setChecked(bool(self.existing_config.get("idle_prefetch_enabled", True)))
            self.idle_prefetch_batch_spin.setValue(int(self.existing_config.get("idle_prefetch_batch", 20)))
            self.url_only_mode_checkbox.setChecked(bool(self.existing_config.get("url_only_mode", False)))
            self.telemetry_checkbox.setChecked(bool(self.existing_config.get("telemetry_enabled", True)))
        except Exception as e:
            logger.warning(f"Error loading config into dialog: {e}")

    def get_config(self) -> dict:
        groq_key = self.groq_input.text().strip()
        gemini_key = self.gemini_input.text().strip()
        gemini_backup_key = self.gemini_backup_input.text().strip()
        gemini_keyword_backup_key = self.gemini_keyword_backup_input.text().strip()
        use_ollama = self.ollama_checkbox.isChecked()

        if not groq_key and not gemini_key and not use_ollama:
            raise ValueError("Vui lòng cấu hình ít nhất một AI provider (Groq, Gemini, hoặc Ollama)")

        try:
            rate_limit_pause = int(self.rate_limit_pause_input.text().strip() or "60")
        except ValueError:
            rate_limit_pause = 60

        mode = self.mode_combo.currentData() or "search"
        enable_imagen = self.enable_imagen_checkbox.isChecked()
        enable_gemini_desc = self.enable_gemini_desc_checkbox.isChecked()
        if mode == "generate":
            enable_imagen = True
            enable_gemini_desc = True

        eval_keys = {}
        for i in range(1, 8):
            if i - 1 < len(self.gemini_eval_inputs):
                eval_keys[f"gemini_eval_api_key_{i}"] = self.gemini_eval_inputs[i - 1].text().strip()

        return {
            "groq_api_key": groq_key,
            "gemini_api_key": gemini_key,
            "gemini_backup_api_key": gemini_backup_key,
            "gemini_keyword_api_key_backup": gemini_keyword_backup_key,
            "use_ollama": use_ollama,
            "ollama_url": self.ollama_url_input.text().strip(),
            "pexels_api_key": self.pexels_input.text().strip(),
            "pixabay_api_key": self.pixabay_input.text().strip(),
            "unsplash_api_key": self.unsplash_input.text().strip(),
            "europeana_api_key": self.europeana_input.text().strip(),
            "klipy_app_key": self.klipy_input.text().strip(),
            "giphy_api_key": self.giphy_input.text().strip(),
            "iconscout_api_token": self.iconscout_input.text().strip(),
            "smithsonian_api_key": self.smithsonian_input.text().strip(),
            "huggingface_api_token": self.huggingface_input.text().strip(),
            "noun_project_api_key": self.noun_project_id_input.text().strip(),
            "noun_project_api_secret": self.noun_project_secret_input.text().strip(),
            "enable_ai_evaluation": self.enable_ai_eval_checkbox.isChecked(),
            **eval_keys,
            "enable_rate_limit_protection": self.enable_rate_limit_checkbox.isChecked(),
            "rate_limit_pause_duration": rate_limit_pause,
            "image_generation_mode": mode,
            "skip_existing_images": self.skip_existing_images_checkbox.isChecked(),
            "imagen_enabled": enable_imagen,
            "imagen_api_key": self.imagen_api_key_input.text().strip(),
            "enable_gemini_image_description": enable_gemini_desc,
            "gemini_image_description_api_key": self.gemini_desc_input.text().strip(),
            "gemini_image_description_api_key_backup_1": self.gemini_desc_backup1_input.text().strip(),
            "gemini_image_description_api_key_backup_2": self.gemini_desc_backup2_input.text().strip(),
            "imagen_default_style": self.imagen_style_combo.currentText(),
            "imagen_default_size": self.imagen_size_combo.currentText(),
            "imagen_fallback_to_search_providers": self.imagen_fallback_checkbox.isChecked(),
            # GĐ5 Pipeline & Cache
            "clip_tier": self.clip_tier_combo.currentData() or "auto",
            "strict_accuracy_mode": self.strict_accuracy_checkbox.isChecked(),
            "idle_prefetch_enabled": self.idle_prefetch_checkbox.isChecked(),
            "idle_prefetch_batch": self.idle_prefetch_batch_spin.value(),
            "url_only_mode": self.url_only_mode_checkbox.isChecked(),
            "telemetry_enabled": self.telemetry_checkbox.isChecked(),
        }

    # ── TEST CONNECTIONS ─────────────────────────────────────────────────────
    def test_connection(self):
        groq_key = self.groq_input.text().strip()
        gemini_key = self.gemini_input.text().strip()
        use_ollama = self.ollama_checkbox.isChecked()
        ollama_url = self.ollama_url_input.text().strip()

        if not (groq_key or gemini_key or use_ollama):
            QMessageBox.warning(self, "Thiếu cấu hình", "Vui lòng nhập API key của ít nhất một AI provider.")
            return

        results = []
        if groq_key:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "test"}], "max_tokens": 5},
                    timeout=5,
                )
                results.append("✓ Groq API: Hoạt động bình thường" if resp.status_code == 200 else f"✗ Groq API: Lỗi {resp.status_code}")
            except Exception as e:
                results.append(f"✗ Groq API: {e}")

        if gemini_key:
            try:
                resp = requests.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
                    params={"key": gemini_key},
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": "test"}]}], "generationConfig": {"maxOutputTokens": 5}},
                    timeout=5,
                )
                results.append("✓ Gemini API: Hoạt động bình thường" if resp.status_code == 200 else f"✗ Gemini API: Lỗi {resp.status_code}")
            except Exception as e:
                results.append(f"✗ Gemini API: {e}")

        if use_ollama:
            try:
                resp = requests.get(f"{ollama_url}/api/tags", timeout=3)
                results.append("✓ Ollama Server: Hoạt động bình thường" if resp.status_code == 200 else f"✗ Ollama Server: Lỗi {resp.status_code}")
            except Exception as e:
                results.append(f"✗ Ollama: Không thể kết nối tới {ollama_url}")

        QMessageBox.information(self, "Kết quả kiểm tra AI", "\n".join(results))

    def test_image_providers(self):
        pexels_key = self.pexels_input.text().strip()
        unsplash_key = self.unsplash_input.text().strip()
        pixabay_key = self.pixabay_input.text().strip()
        europeana_key = self.europeana_input.text().strip()

        results = []

        if pexels_key:
            try:
                r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": pexels_key}, params={"query": "cat", "per_page": 1}, timeout=5)
                results.append(("Pexels", "Hoạt động tốt", r.status_code == 200, "Ảnh Stock chất lượng cao"))
            except Exception as e:
                results.append(("Pexels", str(e), False, "Lỗi kết nối"))
        else:
            results.append(("Pexels", "Chưa nhập API key", None, "Tùy chọn"))

        if pixabay_key:
            try:
                r = requests.get("https://pixabay.com/api/", params={"key": pixabay_key, "q": "cat", "per_page": 3}, timeout=5)
                results.append(("Pixabay", "Hoạt động tốt", r.status_code == 200, "Ảnh Flashcards & Minh họa"))
            except Exception as e:
                results.append(("Pixabay", str(e), False, "Lỗi kết nối"))
        else:
            results.append(("Pixabay", "Chưa nhập API key", None, "Tùy chọn"))

        if unsplash_key:
            try:
                r = requests.get("https://api.unsplash.com/search/photos", headers={"Authorization": f"Client-ID {unsplash_key}"}, params={"query": "cat", "per_page": 1}, timeout=5)
                results.append(("Unsplash", "Hoạt động tốt", r.status_code == 200, "Ảnh nghệ thuật Creative Commons"))
            except Exception as e:
                results.append(("Unsplash", str(e), False, "Lỗi kết nối"))
        else:
            results.append(("Unsplash", "Chưa nhập API key", None, "Tùy chọn"))

        try:
            r = requests.get("https://api.openverse.engineering/v1/images", params={"q": "cat", "page_size": 1}, timeout=5, headers={"User-Agent": "AnkiAI/5.0"})
            results.append(("Openverse", "Hoạt động tốt", r.status_code == 200, "Nguồn ảnh mở miễn phí"))
        except Exception:
            results.append(("Openverse", "Không kết nối được", False, "Miễn phí"))

        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "list": "search", "srsearch": "tree", "srnamespace": "6", "srlimit": 1, "format": "json", "origin": "*"}, headers={"User-Agent": "AnkiAI/5.0"}, timeout=6)
            results.append(("Wikimedia Commons", "Hoạt động tốt", r.status_code == 200, "Kho tư liệu bách khoa"))
        except Exception:
            results.append(("Wikimedia Commons", "Không kết nối được", False, "Miễn phí"))

        if europeana_key:
            try:
                r = requests.get("https://api.europeana.eu/record/v2/search.json", params={"wskey": europeana_key, "query": "cat"}, timeout=5)
                results.append(("Europeana", "Hoạt động tốt", r.status_code == 200, "Di sản văn hóa Châu Âu"))
            except Exception as e:
                results.append(("Europeana", str(e), False, "Lỗi kết nối"))
        else:
            results.append(("Europeana", "Chưa nhập API key", None, "Tùy chọn"))

        tokens = get_tokens()
        dialog = QDialog(self)
        apply_dialog_theme(dialog)
        dialog.setWindowTitle("AnkiAI — Trạng thái nguồn ảnh")
        dialog.setMinimumWidth(560)
        dialog.setMinimumHeight(460)

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(24, 22, 24, 22)
        d_layout.setSpacing(14)
        d_layout.addWidget(header_section(
            "Kiểm tra nguồn ảnh",
            "Trạng thái kết nối tới các dịch vụ hình ảnh.",
            icon="🔍"
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(8)

        for name, status_text, is_ok, desc in results:
            card, c_layout = settings_section()
            row = QHBoxLayout()
            row.setSpacing(14)

            icon_color = tokens["ok"] if is_ok else tokens["danger"] if is_ok is False else tokens["text_low"]
            ic = QLabel("✓" if is_ok else "✗" if is_ok is False else "○")
            ic.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {icon_color}; background: transparent; border: none;")
            ic.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            row.addWidget(ic)

            info_v = QVBoxLayout()
            info_v.setSpacing(2)
            name_lbl = QLabel(name)
            name_lbl.setProperty("fieldLabel", True)
            info_v.addWidget(name_lbl)
            desc_lbl = QLabel(desc)
            desc_lbl.setProperty("hint", True)
            info_v.addWidget(desc_lbl)
            row.addLayout(info_v, stretch=1)

            st = status_badge(
                status_text,
                state="success" if is_ok else "error" if is_ok is False else "muted"
            )
            row.addWidget(st)
            c_layout.addLayout(row)
            b_layout.addWidget(card)

        b_layout.addStretch()
        scroll.setWidget(body)
        d_layout.addWidget(scroll, stretch=1)

        close_btn = QPushButton("Đóng")
        close_btn.setProperty("primary", True)
        close_btn.clicked.connect(dialog.accept)
        d_layout.addWidget(close_btn)
        dialog.exec()


# ============================================================================
# 5. PROGRESS DIALOG
# ============================================================================

class ProgressDialog(QDialog):
    """
    AI Processing Dashboard — real-time batch progress.

    Dark cinematic surface + Electric Blue → Violet gradient progress bar.
    Compact stat counters. Current card feed. Semantic state transitions.
    """

    def __init__(self, total_cards: int, parent=None):
        super().__init__(parent)
        self.total_cards = total_cards
        self.current_card = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.is_cancelled = False
        self._on_cancel_callback = None
        self.init_ui()

    def init_ui(self):
        tokens = get_tokens()
        apply_dialog_theme(self)
        self.setWindowTitle("AnkiAI — Processing")
        self.setMinimumWidth(560)
        self.setMinimumHeight(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        # ── Header row: title + state badge ─────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_v = QVBoxLayout()
        title_v.setSpacing(3)

        self.title_label = QLabel(f"Processing  {self.total_cards}  thẻ")
        self.title_label.setProperty("heading", True)
        title_v.addWidget(self.title_label)

        self.subtitle_label = QLabel("AnkiAI đang tìm và thêm ảnh minh họa…")
        self.subtitle_label.setProperty("subheading", True)
        title_v.addWidget(self.subtitle_label)

        header_row.addLayout(title_v, stretch=1)

        self.state_badge = status_badge("Đang chạy", state="running")
        header_row.addWidget(self.state_badge)
        layout.addLayout(header_row)

        # ── Progress bar ─────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(max(self.total_cards, 1))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("0%")
        layout.addWidget(self.progress_bar)

        # Counter under bar
        counter_row = QHBoxLayout()
        self.lbl_processed = QLabel(f"0 / {self.total_cards}  thẻ")
        self.lbl_processed.setProperty("muted", True)
        counter_row.addWidget(self.lbl_processed)
        counter_row.addStretch()
        layout.addLayout(counter_row)

        # ── Stat summary ─────────────────────────────────────────────────
        stat_wrap, self.success_label, self.skipped_label, self.failed_label = stat_row_widget(0, 0, 0)
        layout.addWidget(stat_wrap)

        # ── Current item card ────────────────────────────────────────────
        current_card, ct_layout = settings_section()
        ct_layout.setSpacing(6)

        ct_row = QHBoxLayout()
        ct_row.setSpacing(10)

        dot = QLabel("▶")
        dot.setStyleSheet(
            f"color: {tokens['accent']}; font-size: 12px; font-weight: 700; "
            f"background: transparent; border: none;"
        )
        dot.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        ct_row.addWidget(dot)

        self.status_label = QLabel("Khởi tạo bộ xử lý…")
        self.status_label.setProperty("fieldLabel", True)
        self.status_label.setWordWrap(True)
        ct_row.addWidget(self.status_label, stretch=1)
        ct_layout.addLayout(ct_row)

        self.detail_label = QLabel("")
        self.detail_label.setProperty("hint", True)
        self.detail_label.setWordWrap(True)
        ct_layout.addWidget(self.detail_label)
        layout.addWidget(current_card)

        layout.addStretch()

        # ── Cancel button ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.cancel_button = QPushButton("⏹  Dừng batch")
        self.cancel_button.setProperty("danger", True)
        self.cancel_button.clicked.connect(self.cancel)
        btn_row.addWidget(self.cancel_button)
        layout.addLayout(btn_row)

    def set_cancel_callback(self, callback: Callable[[], None]):
        self._on_cancel_callback = callback

    def update_progress(self, current: int, total: int, status_msg: str, detail_msg: str = ""):
        self.current_card = current
        self.progress_bar.setValue(current)
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setFormat(f"{pct}%")
        self.lbl_processed.setText(f"{current} / {total}  thẻ")
        self.status_label.setText(status_msg)
        if detail_msg:
            self.detail_label.setText(detail_msg)
        QApplication.processEvents()

    def update_stats(self, successful: int, skipped: int, failed: int):
        self.successful = successful
        self.skipped = skipped
        self.failed = failed
        self.success_label.setText(f"✓  {successful}")
        self.skipped_label.setText(f"⊘  {skipped}")
        self.failed_label.setText(f"✗  {failed}")

    def cancel(self):
        tokens = get_tokens()
        self.is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Đang dừng…")
        self.state_badge.setText("⏸  Đã tạm dừng")
        self.state_badge.setStyleSheet(
            f"color: {tokens['warn']}; background-color: {tokens['warn_dim']}; "
            f"border: 1px solid {tokens['warn']}; border-radius: 5px; "
            f"padding: 2px 9px; font-size: 11px; font-weight: 700;"
        )
        if self._on_cancel_callback:
            self._on_cancel_callback()

    def finish(self, success_count: int, skipped_count: int, fail_count: int):
        tokens = get_tokens()
        self.progress_bar.setValue(self.total_cards)
        self.progress_bar.setFormat("100%")

        self.title_label.setText("✓  Batch hoàn tất")
        self.subtitle_label.setText("Đã xử lý xong toàn bộ danh sách thẻ.")

        self.state_badge.setText("✓  Hoàn tất")
        self.state_badge.setStyleSheet(
            f"color: {tokens['ok']}; background-color: {tokens['ok_dim']}; "
            f"border: 1px solid {tokens['ok']}; border-radius: 5px; "
            f"padding: 2px 9px; font-size: 11px; font-weight: 700;"
        )

        self.status_label.setText("Tất cả thẻ trong batch đã được xử lý.")
        self.detail_label.setText("")

        self.cancel_button.setText("Đóng")
        self.cancel_button.setProperty("danger", False)
        self.cancel_button.setProperty("primary", True)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setStyleSheet("")
        try:
            self.cancel_button.clicked.disconnect()
        except Exception:
            pass
        self.cancel_button.clicked.connect(self.accept)
        self.update_stats(success_count, skipped_count, fail_count)

    def showEvent(self, event):
        """Staggered entrance animation on first display."""
        super().showEvent(event)
        _animate_entrance(self)


# ============================================================================
# 6. HELPER FUNCTIONS
# ============================================================================

def get_note_data(note) -> tuple:
    """Extract (vocabulary, definition) from an Anki Note."""
    try:
        fields = {name: note[name] for name in note.keys()}
        vocabulary = (
            fields.get("Front") or
            fields.get("Mặt trước") or
            fields.get("Word") or
            fields.get("Question") or
            (list(fields.values())[0] if fields else "")
        )
        definition = (
            fields.get("Back") or
            fields.get("Mặt sau") or
            fields.get("Definition") or
            fields.get("Định nghĩa") or
            fields.get("Answer") or
            (list(fields.values())[1] if len(fields) > 1 else "")
        )
        vocabulary = re.sub(r"<[^>]+>", "", vocabulary).strip()
        definition = re.sub(r"<[^>]+>", "", definition).strip()
        return vocabulary, definition
    except Exception as e:
        logger.warning(f"Error getting note data: {e}")
        return "", ""


# ============================================================================
# 7. GĐ5 WIDGETS — Feedback, Quota Display, Verification Badge  [MS §18]
# ============================================================================

class FeedbackWidget(QWidget):
    """👍 / 👎 buttons for a single image result.

    Call ``on_vote(callback)`` to register a handler: ``callback(word, vote)``.

    Usage::

        fb = FeedbackWidget(word="tactics")
        fb.on_vote(lambda w, v: telemetry.feedback(w, v))
    """

    def __init__(self, word: str = "", parent=None):
        super().__init__(parent)
        self._word = word
        self._vote_callback: Optional[Callable] = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._up_btn = QToolButton()
        self._up_btn.setText("👍")
        self._up_btn.setToolTip("Ảnh này phù hợp")
        self._up_btn.clicked.connect(lambda: self._vote("👍"))
        layout.addWidget(self._up_btn)

        self._down_btn = QToolButton()
        self._down_btn.setText("👎")
        self._down_btn.setToolTip("Ảnh này không phù hợp")
        self._down_btn.clicked.connect(lambda: self._vote("👎"))
        layout.addWidget(self._down_btn)

        layout.addStretch()

    def on_vote(self, callback: Callable):
        """Register a handler: ``callback(word, "👍" | "👎")``."""
        self._vote_callback = callback

    def _vote(self, vote: str):
        self._up_btn.setEnabled(False)
        self._down_btn.setEnabled(False)
        if self._vote_callback:
            self._vote_callback(self._word, vote)

    @property
    def word(self) -> str:
        return self._word


class QuotaDisplayWidget(QWidget):
    """Compact quota remaining readout from QuotaManager.

    Shows per-model: ``Groq: 12,340/14,400 today`` etc.
    Updates when ``refresh()`` is called.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        title = QLabel("AI Hạn mức hôm nay")
        title.setProperty("fieldLabel", True)
        layout.addWidget(title)

        self._labels: Dict[str, QLabel] = {}
        for model_key in ("groq_workhorse", "groq_hard", "gemini_vision"):
            lbl = QLabel(f"{model_key}: —")
            lbl.setProperty("hint", True)
            layout.addWidget(lbl)
            self._labels[model_key] = lbl

    def refresh(self, quota_manager=None):
        """Update display from a QuotaManager snapshot."""
        if quota_manager is None:
            return
        try:
            snap = quota_manager.snapshot()
        except Exception:
            return
        for key, lbl in self._labels.items():
            bucket = snap.get(key)
            if bucket:
                used = bucket.get("rpd_used", 0)
                limit = bucket.get("rpd_limit", 0)
                remaining = max(limit - used, 0)
                lbl.setText(f"{key}: {remaining:,}/{limit:,}")
                # Color-code: green if >50%, yellow if >20%, red if ≤20%
                if limit > 0:
                    pct = remaining / limit
                    tokens = get_tokens()
                    if pct > 0.5:
                        color = tokens.get("success", "#4CAF50")
                    elif pct > 0.2:
                        color = tokens.get("warning", "#FF9800")
                    else:
                        color = tokens.get("danger", "#F44336")
                    lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            else:
                lbl.setText(f"{key}: không có")


class VerificationBadge(QLabel):
    """✓ QC-verified  /  ⚠ unverified  badge for a card.

    Usage::

        badge = VerificationBadge(verified=True)
        badge.set_verified(False)  # update later
    """

    def __init__(self, verified: bool = False, parent=None):
        super().__init__(parent)
        self.set_verified(verified)

    def set_verified(self, verified: bool):
        self._verified = verified
        tokens = get_tokens()
        if verified:
            self.setText("✓ QC-verified")
            self.setStyleSheet(
                f"color: {tokens['ok']}; "
                f"background: {tokens['ok_dim']}; "
                f"border: 1px solid {tokens['ok']}; "
                f"border-radius: 4px; padding: 1px 7px; font-size: 11px; "
                f"font-weight: 600;"
            )
        else:
            self.setText("⚠ unverified")
            self.setStyleSheet(
                f"color: {tokens['warn']}; "
                f"background: {tokens['warn_dim']}; "
                f"border: 1px solid {tokens['warn']}; "
                f"border-radius: 4px; padding: 1px 7px; font-size: 11px; "
                f"font-weight: 600;"
            )

    @property
    def verified(self) -> bool:
        return self._verified
