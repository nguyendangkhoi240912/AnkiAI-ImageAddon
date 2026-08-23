"""Automated verification test suite for AnkiAI UI redesign with complete mocks."""

import sys
import os
import unittest
from unittest.mock import MagicMock

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
        self.assertEqual(dark_tokens["bg_window"], "#0a0e14")
        self.assertEqual(light_tokens["bg_window"], "#eef2f7")
        self.assertEqual(dark_tokens["accent"], "#00b4d8")
        self.assertEqual(light_tokens["accent"], "#0070c0")
        
        qss_dark = build_stylesheet(dark=True)
        qss_light = build_stylesheet(dark=False)
        self.assertIn("QDialog", qss_dark)
        self.assertIn("QTabWidget", qss_dark)
        self.assertIn("#0a0e14", qss_dark)
        self.assertIn("#eef2f7", qss_light)

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
            # 🆕 v6.1 new providers
            "smithsonian_api_key": "smithsonian_key_123",
            "huggingface_api_token": "hf_token_123",
            "noun_project_api_key": "noun_client_id_123",
            "noun_project_api_secret": "noun_client_secret_123",
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
        # 🆕 v6.1 new providers verification
        self.assertEqual(saved["smithsonian_api_key"], "smithsonian_key_123")
        self.assertEqual(saved["huggingface_api_token"], "hf_token_123")
        self.assertEqual(saved["noun_project_api_key"], "noun_client_id_123")
        self.assertEqual(saved["noun_project_api_secret"], "noun_client_secret_123")

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
