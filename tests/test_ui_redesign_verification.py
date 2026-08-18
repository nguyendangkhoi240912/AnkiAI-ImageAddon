"""Automated verification test suite for AnkiAI UI redesign with complete mocks."""

import sys
import os
import unittest
from unittest.mock import MagicMock

# Setup mock aqt before any imports
class MockWidget(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text = ""
        self._value = 0
        self._checked = False
        self._items = []
        self._properties = {}
        self._current_text = ""

    def setText(self, val):
        self._text = str(val)

    def text(self):
        return self._text

    def setValue(self, val):
        self._value = int(val)

    def value(self):
        return self._value

    def setChecked(self, val):
        self._checked = bool(val)

    def isChecked(self):
        return self._checked

    def addItems(self, items):
        self._items.extend(items)
        if self._items and not self._current_text:
            self._current_text = self._items[0]

    def addItem(self, text, data=None):
        self._items.append(text)
        if not self._current_text:
            self._current_text = text

    def setCurrentText(self, text):
        self._current_text = text

    def currentText(self):
        return self._current_text

    def findData(self, data):
        return 0

    def currentData(self):
        return "search"

    def setProperty(self, k, v):
        self._properties[k] = v

class MockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == "aqt" or fullname.startswith("aqt."):
            from importlib.machinery import ModuleSpec
            return ModuleSpec(fullname, self)
        return None

    def create_module(self, spec):
        fullname = spec.name
        if fullname == "aqt":
            import types
            m = types.ModuleType("aqt")
            m.mw = MagicMock()
            m.gui_hooks = MagicMock()
            m.__path__ = []
            return m
        elif fullname == "aqt.qt":
            import types
            m = types.ModuleType("aqt.qt")
            widgets = [
                "QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QComboBox",
                "QPushButton", "QWidget", "QProgressBar", "QLineEdit", "QTextBrowser",
                "QCheckBox", "QSpinBox", "QFrame", "QScrollArea", "QTabWidget",
                "QToolButton", "QSizePolicy", "QMessageBox", "QApplication"
            ]
            for w in widgets:
                setattr(m, w, MockWidget)
            m.QDialog.DialogCode = MagicMock()
            m.QDialog.DialogCode.Accepted = 1
            m.QDialog.DialogCode.Rejected = 0
            m.QLineEdit.EchoMode = MagicMock()
            m.QLineEdit.EchoMode.Password = 2
            m.QLineEdit.EchoMode.Normal = 0
            m.QFrame.Shape = MagicMock()
            m.QFrame.Shape.HLine = 4
            m.QSizePolicy.Policy = MagicMock()
            m.QSizePolicy.Policy.Fixed = 0
            m.QMessageBox.StandardButton = MagicMock()
            m.QMessageBox.StandardButton.Yes = 16384
            return m
        elif fullname == "aqt.browser":
            import types
            m = types.ModuleType("aqt.browser")
            m.Browser = MagicMock
            return m
        return MagicMock()

    def exec_module(self, module):
        pass

sys.meta_path.insert(0, MockFinder())
sys.path.insert(0, os.path.abspath("."))

from AnkiAI_ImageAddon.modules.ui_theme import get_tokens, build_stylesheet, is_dark_mode, apply_dialog_theme
from AnkiAI_ImageAddon.modules.ui_widgets import (
    header_section,
    settings_section,
    CredentialField,
    credential_field,
    status_badge,
    info_banner,
)
from AnkiAI_ImageAddon.modules.ui import (
    BrowserMenuManager,
    BatchOptionsDialog,
    FieldSelectionDialog,
    ConfigDialog,
    ProgressDialog,
    get_note_data,
)

class TestUIRedesign(unittest.TestCase):
    def test_01_theme_tokens_and_stylesheet(self):
        dark_tokens = get_tokens(dark=True)
        light_tokens = get_tokens(dark=False)
        self.assertEqual(dark_tokens["bg_window"], "#13141f")
        self.assertEqual(light_tokens["bg_window"], "#f8fafc")
        self.assertEqual(dark_tokens["accent"], "#14b8a6")
        self.assertEqual(light_tokens["accent"], "#0d9488")
        
        qss_dark = build_stylesheet(dark=True)
        qss_light = build_stylesheet(dark=False)
        self.assertIn("QDialog", qss_dark)
        self.assertIn("QTabWidget", qss_dark)
        self.assertIn("#13141f", qss_dark)
        self.assertIn("#f8fafc", qss_light)

    def test_02_ui_widgets_primitives(self):
        h = header_section("Title", "Subtitle", icon="⭐")
        self.assertIsNotNone(h)
        frame, layout = settings_section("Card Title", "Card Subtitle")
        self.assertIsNotNone(frame)
        cred = CredentialField("placeholder")
        cred.setText("my_key")
        self.assertEqual(cred.text(), "my_key")
        cred._toggle_visibility()
        self.assertTrue(cred.is_revealed)
        cred._toggle_visibility()
        self.assertFalse(cred.is_revealed)

    def test_03_field_selection_dialog(self):
        avail = ["Front", "Back", "Example", "Image"]
        fsd = FieldSelectionDialog("Basic", avail, initial={"vocabulary_field": "Front", "definition_field": "Back", "examples_field": "Example", "image_field": "Image"})
        fsd.accept_with_values("Front", "Back", "Example", "Image")
        self.assertEqual(fsd.selected_vocab_field, "Front")
        self.assertEqual(fsd.selected_definition_field, "Back")
        self.assertEqual(fsd.selected_examples_field, "Example")
        self.assertEqual(fsd.selected_image_field, "Image")

    def test_04_batch_options_dialog(self):
        bod = BatchOptionsDialog(selected_count=100, default_max=50, pending_count=20)
        bod.max_spin.setValue(50)
        bod._accept_normal()
        self.assertFalse(bod.use_pending)
        self.assertEqual(bod.max_notes, 50)
        bod._accept_pending()
        self.assertTrue(bod.use_pending)

    def test_05_config_dialog(self):
        sample_cfg = {
            "groq_api_key": "gsk_test123",
            "gemini_api_key": "AIzaSyTestKey",
            "gemini_backup_api_key": "AIzaSyBackup1",
            "gemini_keyword_api_key_backup": "AIzaSyBackup2",
            "use_ollama": True,
            "ollama_url": "http://localhost:11434",
            "pexels_api_key": "pexels_key_123",
            "pixabay_api_key": "pixabay_key_123",
            "unsplash_api_key": "unsplash_key_123",
            "europeana_api_key": "europeana_key_123",
            "klipy_app_key": "klipy_123",
            "giphy_api_key": "giphy_123",
            "tenor_api_key": "tenor_123",
            "iconscout_api_token": "iconscout_123",
            "enable_ai_evaluation": True,
            "gemini_eval_api_key_1": "eval1",
            "gemini_eval_api_key_2": "eval2",
            "gemini_eval_api_key_3": "eval3",
            "gemini_eval_api_key_4": "eval4",
            "gemini_eval_api_key_5": "eval5",
            "gemini_eval_api_key_6": "eval6",
            "gemini_eval_api_key_7": "eval7",
            "enable_rate_limit_protection": True,
            "rate_limit_pause_duration": 45,
            "image_generation_mode": "smart",
            "skip_existing_images": False,
            "imagen_enabled": True,
            "imagen_api_key": "imagen_key_123",
            "enable_gemini_image_description": True,
            "gemini_image_description_api_key": "desc_key_main",
            "gemini_image_description_api_key_backup_1": "desc_b1",
            "gemini_image_description_api_key_backup_2": "desc_b2",
            "imagen_default_style": "cartoon",
            "imagen_default_size": "512x512",
            "imagen_fallback_to_search_providers": False,
        }
        cd = ConfigDialog(existing_config=sample_cfg)
        saved = cd.get_config()
        self.assertEqual(saved["groq_api_key"], "gsk_test123")
        self.assertEqual(saved["gemini_api_key"], "AIzaSyTestKey")
        self.assertEqual(saved["gemini_backup_api_key"], "AIzaSyBackup1")
        self.assertEqual(saved["gemini_keyword_api_key_backup"], "AIzaSyBackup2")
        self.assertTrue(saved["use_ollama"])
        self.assertEqual(saved["ollama_url"], "http://localhost:11434")
        self.assertEqual(saved["pexels_api_key"], "pexels_key_123")
        self.assertEqual(saved["gemini_eval_api_key_1"], "eval1")
        self.assertEqual(saved["gemini_eval_api_key_7"], "eval7")
        self.assertEqual(saved["imagen_api_key"], "imagen_key_123")

    def test_06_progress_dialog(self):
        pd = ProgressDialog(total_cards=100)
        pd.update_progress(50, 100, "Đang xử lý thẻ 50/100", "Pexels search")
        pd.update_stats(45, 3, 2)
        self.assertEqual(pd.successful, 45)
        self.assertEqual(pd.skipped, 3)
        self.assertEqual(pd.failed, 2)
        pd.cancel()
        self.assertTrue(pd.is_cancelled)
        pd.finish(45, 3, 2)

    def test_07_get_note_data(self):
        note = {"Front": "<div>hello world</div>", "Back": "xin chao"}
        v, d = get_note_data(note)
        self.assertEqual(v, "hello world")
        self.assertEqual(d, "xin chao")

if __name__ == "__main__":
    unittest.main()
