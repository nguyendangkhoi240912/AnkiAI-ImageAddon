"""Pytest configuration and shared fixtures."""

import pytest
import sys
import os

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