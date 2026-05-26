"""Integration tests for animated domain search."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from AnkiAI_ImageAddon.modules.image_providers import SmartImageSelector, ImageScore
from AnkiAI_ImageAddon.modules.provider_registry import (
    build_smart_selector,
    resolve_domains,
    ANIMATED_FALLBACK_PROVIDERS,
)


class TestAnimatedDomainSearch:
    """Integration tests for animated image search."""

    def test_animated_domain_resolves_correctly(self):
        """Test that 'animated' domain resolves to correct provider IDs."""
        domains = resolve_domains("animated", enable_routing=True)
        assert domains == {"animated"}

    def test_animated_providers_in_domain(self):
        """Test that animated providers are in the animated domain."""
        from AnkiAI_ImageAddon.modules.provider_registry import DOMAIN_PROVIDERS
        
        animated_providers = DOMAIN_PROVIDERS.get("animated", [])
        expected = {"klipy", "giphy", "tenor", "pixabay_animated", "iconscout"}
        assert set(animated_providers) == expected

    def test_search_smart_with_animated_domain(self):
        """Test that search_smart with animated domain returns animated provider results."""
        # Create a mock provider that returns a known result
        mock_provider = Mock()
        mock_provider.name = "giphy"
        mock_provider.search.return_value = [
            {"url": "https://media.giphy.com/test.gif", "title": "test", "provider": "giphy"}
        ]

        selector = SmartImageSelector(max_workers=1)
        selector.add_provider("giphy", mock_provider, domains={"animated"})

        results = selector.search_smart("test", top_n=1, domains={"animated"})

        assert len(results) == 1
        assert "giphy.com" in results[0]
        mock_provider.search.assert_called_once()

    def test_fallback_providers_used_when_no_animated(self):
        """Test that fallback providers are used when no animated providers configured."""
        # Create a mock provider for fallback
        mock_provider = Mock()
        mock_provider.name = "giphy"
        mock_provider.search.return_value = [
            {"url": "https://media.giphy.com/fallback.gif", "title": "fallback", "provider": "giphy"}
        ]

        selector = SmartImageSelector(max_workers=1)
        selector.add_provider("giphy", mock_provider, domains={"animated"})

        # Search with fallback_providers
        results = selector.search_smart(
            "test",
            top_n=1,
            domains=set(),  # Empty domain set
            fallback_providers=ANIMATED_FALLBACK_PROVIDERS,
        )

        # Should still get results from fallback
        assert len(results) == 1

    def test_cache_works_for_animated_search(self):
        """Test that cache is populated and used for animated searches."""
        mock_provider = Mock()
        mock_provider.name = "giphy"
        mock_provider.search.return_value = [
            {"url": "https://media.giphy.com/cached.gif", "title": "cached", "provider": "giphy"}
        ]

        selector = SmartImageSelector(max_workers=1)
        selector.add_provider("giphy", mock_provider, domains={"animated"})

        # First search
        results1 = selector.search_smart("test", top_n=1, domains={"animated"})
        
        # Second search should use cache
        results2 = selector.search_smart("test", top_n=1, domains={"animated"})

        assert results1 == results2
        # Provider should only be called once due to caching
        assert mock_provider.search.call_count == 1


class TestProviderStats:
    """Tests for provider statistics tracking."""

    def test_provider_stats_record_success(self):
        """Test that provider stats record successful requests."""
        from AnkiAI_ImageAddon.modules.image_providers import ProviderStats

        stats = ProviderStats("test_provider")
        stats.record_success(0.5)

        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.avg_response_time > 0

    def test_provider_stats_record_failure(self):
        """Test that provider stats record failed requests."""
        from AnkiAI_ImageAddon.modules.image_providers import ProviderStats

        stats = ProviderStats("test_provider")
        stats.record_failure()

        assert stats.total_requests == 1
        assert stats.failed_requests == 1

    def test_provider_overall_score(self):
        """Test that overall score is calculated correctly."""
        from AnkiAI_ImageAddon.modules.image_providers import ProviderStats

        stats = ProviderStats("test_provider")
        stats.record_success(0.5)
        stats.record_success(0.3)
        stats.record_failure()

        score = stats.get_overall_score()
        assert 0 <= score <= 1