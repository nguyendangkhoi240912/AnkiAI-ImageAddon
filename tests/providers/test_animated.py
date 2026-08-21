"""Unit tests for animated image providers (KLIPY, GIPHY, PixabayAnimated, IconScout)."""

import pytest
from unittest.mock import Mock, patch
import requests

from AnkiAI_ImageAddon.modules.providers.animated import (
    KLIPYProvider,
    GIPHYProvider,
    PixabayAnimatedProvider,
    IconScoutProvider,
)
from AnkiAI_ImageAddon.modules.providers.base import ImageProviderError


class TestKLIPYProvider:
    """Tests for KLIPYProvider."""

    def test_init_requires_key(self):
        """Test that KLIPYProvider requires an app key."""
        with pytest.raises(ImageProviderError, match="KLIPY app key required"):
            KLIPYProvider("")

    def test_search_success(self):
        """Test successful search returns image URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": [
                    {
                        "title": "test gif",
                        "file": {
                            "md": {"gif": {"url": "https://example.com/test.gif"}}
                        }
                    }
                ]
            }
        }

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = KLIPYProvider("test_key")
            results = provider.search("test", per_page=1)

            assert len(results) == 1
            assert results[0]["url"] == "https://example.com/test.gif"

    def test_search_empty_results(self):
        """Test that empty results raise ImageProviderError."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"data": []}}

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = KLIPYProvider("test_key")
            with pytest.raises(ImageProviderError, match="No results"):
                provider.search("test", per_page=1)

    def test_search_rate_limit(self):
        """Test that 429 response raises ImageProviderError."""
        mock_response = Mock()
        mock_response.status_code = 429

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = KLIPYProvider("test_key")
            with pytest.raises(ImageProviderError, match="429"):
                provider.search("test", per_page=1)


class TestGIPHYProvider:
    """Tests for GIPHYProvider."""

    def test_init_requires_key(self):
        """Test that GIPHYProvider requires an API key."""
        with pytest.raises(ImageProviderError, match="GIPHY API key required"):
            GIPHYProvider("")

    def test_search_success(self):
        """Test successful search returns image URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "title": "funny cat",
                    "images": {"original": {"url": "https://media.giphy.com/funny.gif"}}
                }
            ]
        }

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = GIPHYProvider("test_key")
            results = provider.search("cat", per_page=1)

            assert len(results) == 1
            assert "giphy.com" in results[0]["url"]


class TestPixabayAnimatedProvider:
    """Tests for PixabayAnimatedProvider."""

    def test_init_requires_key(self):
        """Test that PixabayAnimatedProvider requires an API key."""
        with pytest.raises(ImageProviderError, match="Pixabay API key required"):
            PixabayAnimatedProvider("")

    def test_search_success(self):
        """Test successful search returns image URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "webformatURL": "https://pixabay.com/animated.gif",
                    "tags": "animation"
                }
            ]
        }

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = PixabayAnimatedProvider("test_key")
            results = provider.search("animation", per_page=1)

            assert len(results) == 1
            assert "pixabay.com" in results[0]["url"]


class TestIconScoutProvider:
    """Tests for IconScoutProvider."""

    def test_init_without_token(self):
        """Test that IconScoutProvider can be initialized without token."""
        provider = IconScoutProvider()
        assert provider.name == "iconscout"

    def test_search_success(self):
        """Test successful search returns image URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "data": [
                    {
                        "name": "arrow icon",
                        "download_url": "https://iconscout.com/arrow.gif"
                    }
                ]
            }
        }

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = IconScoutProvider("test_token")
            results = provider.search("arrow", per_page=1)

            assert len(results) == 1
            assert "iconscout.com" in results[0]["url"]

    def test_search_all_endpoints_fail(self):
        """Test that all failed endpoints raise ImageProviderError."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch("AnkiAI_ImageAddon.modules.providers.animated._ImageProviderSessionManager.get_session") as mock_session_mgr:
            mock_session = Mock()
            mock_session.get.return_value = mock_response
            mock_session_mgr.return_value = mock_session

            provider = IconScoutProvider("test_token")
            with pytest.raises(ImageProviderError):
                provider.search("test", per_page=1)