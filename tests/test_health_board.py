"""
Tests for image_providers/health.py — GĐ2, G2.6
Chạy độc lập, không cần Anki/Qt.
"""
import sys
import os
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AnkiAI_ImageAddon.image_providers.health import HealthBoard, get_health_board


class TestHealthBoard:
    @pytest.fixture
    def hb(self):
        return HealthBoard(alpha=0.5)  # fast adaptation for testing

    def test_order_unknown_providers(self, hb):
        """Unseen providers should be accepted without error."""
        result = hb.order(["pixabay", "wikimedia", "pexels"])
        assert set(result) == {"pixabay", "wikimedia", "pexels"}

    def test_order_preserves_all_providers(self, hb):
        providers = ["pixabay", "wikimedia", "pexels", "unsplash"]
        hb.report("wikimedia", 0.2, True)
        result = hb.order(providers)
        assert set(result) == set(providers)

    def test_fast_reliable_provider_ranks_first(self, hb):
        hb.report("slow_provider", 3.0, True)
        hb.report("fast_provider", 0.1, True)
        result = hb.order(["slow_provider", "fast_provider"])
        assert result[0] == "fast_provider"

    def test_down_provider_pushed_to_end(self, hb):
        """Provider with success_ema below threshold → pushed to end."""
        # Drive success_ema below threshold
        for _ in range(10):
            hb.report("bad_provider", 0.5, False)
        hb.report("good_provider", 0.5, True)
        result = hb.order(["bad_provider", "good_provider"])
        assert result[-1] == "bad_provider"

    def test_report_updates_stats(self, hb):
        hb.report("pixabay", 0.3, True)
        snap = hb.snapshot()
        assert "pixabay" in snap
        assert snap["pixabay"]["call_count"] == 1
        assert snap["pixabay"]["latency_ema"] != 1.0  # changed from default

    def test_report_thread_safe(self, hb):
        """Multiple threads reporting concurrently should not raise."""
        import threading
        errors = []

        def worker(name, n):
            for _ in range(n):
                try:
                    hb.report(name, 0.1, True)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"p{i}", 50)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"Thread errors: {errors}"

    def test_reset_single_provider(self, hb):
        hb.report("pixabay", 0.5, True)
        hb.reset("pixabay")
        snap = hb.snapshot()
        assert "pixabay" not in snap

    def test_reset_all(self, hb):
        hb.report("pixabay", 0.5, True)
        hb.report("wikimedia", 0.3, True)
        hb.reset()
        assert hb.snapshot() == {}

    def test_empty_provider_list(self, hb):
        assert hb.order([]) == []

    def test_singleton(self):
        hb1 = get_health_board()
        hb2 = get_health_board()
        assert hb1 is hb2

    def test_ema_convergence(self):
        """EMA should converge toward real latency over many calls."""
        hb = HealthBoard(alpha=0.3)
        for _ in range(30):
            hb.report("p", 0.1, True)
        snap = hb.snapshot()
        # After 30 calls with alpha=0.3, EMA of latency should be close to 0.1
        assert abs(snap["p"]["latency_ema"] - 0.1) < 0.05

    def test_order_single_provider(self, hb):
        hb.report("only", 0.5, True)
        assert hb.order(["only"]) == ["only"]
