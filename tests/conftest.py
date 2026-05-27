"""Pytest configuration and shared fixtures."""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Mock aqt and Anki modules before any imports
import sys
from unittest.mock import MagicMock

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
            
            import types
            m = types.ModuleType("aqt")
            m.mw = MockMW()
            m.gui_hooks = MagicMock()
            m.__path__ = []
            return m
        return MagicMock()

    def exec_module(self, module):
        pass

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
        "tenor_api_key": "test_tenor_key",
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