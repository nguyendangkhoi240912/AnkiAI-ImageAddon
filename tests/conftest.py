"""Pytest configuration and shared fixtures."""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Mock aqt and Anki modules before any imports
import types

class MockWidget:
    def __init__(self, *args, **kwargs):
        self._text = ""
        self._value = 0
        self._checked = False
        self._items = []
        self._properties = {}
        self._current_text = ""
        self.clicked = MagicMock()
        self.textChanged = MagicMock()
        self.stateChanged = MagicMock()

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

    def __getattr__(self, name):
        mock = MagicMock()
        setattr(self, name, mock)
        return mock


class MockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == "aqt" or fullname.startswith("aqt."):
            from importlib.machinery import ModuleSpec
            return ModuleSpec(fullname, self)
        return None

    def create_module(self, spec):
        fullname = spec.name
        if fullname == "aqt":
            class MockMW:
                def __init__(self):
                    self.addonManager = MagicMock()
                    self.addonManager.getConfig.return_value = {}
                    self.col = MagicMock()
            
            m = types.ModuleType("aqt")
            m.mw = MockMW()
            m.gui_hooks = MagicMock()
            m.__path__ = []
            return m
        elif fullname == "aqt.qt":
            class QtModule(types.ModuleType):
                def __getattr__(self, name):
                    return MockWidget

            m = QtModule("aqt.qt")
            widgets = [
                "QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QComboBox",
                "QPushButton", "QWidget", "QProgressBar", "QLineEdit", "QTextBrowser",
                "QCheckBox", "QSpinBox", "QFrame", "QScrollArea", "QTabWidget",
                "QToolButton", "QSizePolicy", "QMessageBox", "QApplication", "QTimer",
                "QAction", "QMenu", "Qt"
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
            m.QApplication.processEvents = staticmethod(lambda *a, **kw: None)
            m.pyqtSignal = MagicMock
            return m
        elif fullname == "aqt.browser":
            m = types.ModuleType("aqt.browser")
            m.Browser = MagicMock
            return m
        return MagicMock()

    def exec_module(self, module):
        pass

if not any(isinstance(f, MockFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, MockFinder())

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "pexels_api_key": "test_pexels_key",
        "unsplash_api_key": "test_unsplash_key",
        "pixabay_api_key": "test_pixabay_key",
        "klipy_app_key": "test_klipy_key",
        "giphy_api_key": "test_giphy_key",
        "iconscout_api_token": "test_iconscout_token",
        "enable_ai_provider_routing": True,
        "max_concurrent_providers": 5,
    }


@pytest.fixture
def minimal_config():
    """Minimal configuration with no API keys."""
    return {
        "enable_ai_provider_routing": False,
        "max_concurrent_providers": 5,
    }