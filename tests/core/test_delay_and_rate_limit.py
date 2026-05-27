"""Tests for AdaptiveDelayManager and RateLimitHandler."""

import pytest
import time
from unittest.mock import patch

from AnkiAI_ImageAddon.modules.image_providers import AdaptiveDelayManager, RateLimitHandler


class TestAdaptiveDelayManager:
    """Tests for AdaptiveDelayManager."""

    def test_initial_delay_is_base(self):
        """Test that initial delay equals base_delay."""
        manager = AdaptiveDelayManager(base_delay_ms=100, max_delay_ms=2000)
        assert manager.get_delay("test_provider") == 0.1

    def test_increase_delay_caps_at_max(self):
        """Test that delay increase caps at max_delay."""
        manager = AdaptiveDelayManager(base_delay_ms=100, max_delay_ms=200)
        
        # Increase multiple times
        for _ in range(10):
            manager.increase_delay("test_provider", is_rate_limit=False)
        
        # Should be capped at max
        assert manager.get_delay("test_provider") <= 0.2

    def test_reset_delay_if_expired(self):
        """Test that delay resets after expiration time."""
        manager = AdaptiveDelayManager(base_delay_ms=100, max_delay_ms=2000)
        manager.increase_delay("test_provider", is_rate_limit=True)
        
        # Not expired yet
        manager.reset_delay_if_expired("test_provider", reset_hours=1)
        assert manager.get_delay("test_provider") > 0.1
        
        # Simulate time passing by modifying last_failure_time
        manager.last_failure_time["test_provider"] = time.time() - 7200  # 2 hours ago
        manager.reset_delay_if_expired("test_provider", reset_hours=1)
        
        # Should be reset to base
        assert manager.get_delay("test_provider") == 0.1

    def test_apply_delay(self):
        """Test that apply_delay actually sleeps."""
        manager = AdaptiveDelayManager(base_delay_ms=100, max_delay_ms=200)
        
        start = time.time()
        manager.apply_delay("test_provider")
        elapsed = time.time() - start
        
        # Should have slept for at least base_delay
        assert elapsed >= 0.1


class TestRateLimitHandler:
    """Tests for RateLimitHandler."""

    def test_not_rate_limited_initially(self):
        """Test that provider is not rate limited initially."""
        handler = RateLimitHandler()
        assert not handler.is_rate_limited("test_provider")

    def test_rate_limited_after_handle(self):
        """Test that provider is rate limited after handle_rate_limit."""
        handler = RateLimitHandler()
        handler.handle_rate_limit("test_provider")
        
        assert handler.is_rate_limited("test_provider")

    def test_rate_limit_expires(self):
        """Test that rate limit expires after pause duration."""
        handler = RateLimitHandler()
        handler.handle_rate_limit("test_provider")
        
        # Simulate expiration by shifting last_rate_limit back in time
        from datetime import timedelta
        handler.last_rate_limit["test_provider"] -= timedelta(seconds=5)
        
        assert not handler.is_rate_limited("test_provider")

    def test_wait_if_limited(self):
        """Test wait_if_limited returns correct boolean."""
        handler = RateLimitHandler()
        
        # Not limited
        assert not handler.wait_if_limited("test_provider")
        
        # Limited
        handler.handle_rate_limit("test_provider")
        assert handler.wait_if_limited("test_provider")