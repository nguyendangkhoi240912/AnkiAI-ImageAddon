"""
Telemetry Collector Tests — GĐ5, G5.4                      [MS §15, §20]
=========================================================================
Test the TelemetryCollector wrapper and its adjustment-suggestion logic.

QuotaManager tests already exist in ``test_quota.py`` (12 tests from G4.4).
"""
import pytest

from AnkiAI_ImageAddon.modules.cache import CacheManager
from AnkiAI_ImageAddon.modules.telemetry import (
    TelemetryCollector,
    get_telemetry_collector,
    reset_telemetry_collector,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cache(tmp_path):
    user_files = tmp_path / "user_files"
    user_files.mkdir(exist_ok=True)
    cm = CacheManager(str(user_files))
    yield cm
    cm.close()


@pytest.fixture
def tc(cache):
    return TelemetryCollector(cache)


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TestRecord:
    def test_record_stores_entry(self, tc, cache):
        tc.record(word="tactics", group="F", resolved_by="clip|qc", latency_ms=2800)
        summary = cache.telemetry_summary(since_days=7)
        assert len(summary) >= 1
        assert summary[0]["group"] == "F"

    def test_record_with_clip_score(self, tc, cache):
        tc.record(word="apple", group="A", clip_score=0.85, latency_ms=600)
        summary = cache.telemetry_summary(since_days=7)
        assert summary[0]["avg_clip_score"] > 0.5


# ---------------------------------------------------------------------------
# Feedback (👍/👎)
# ---------------------------------------------------------------------------

class TestFeedback:
    def test_thumbs_up_recorded(self, tc, cache):
        tc.record(word="happy", group="E")
        tc.feedback("happy", "👍")
        entries = tc.recent_entries("happy")
        assert entries[0]["user_feedback"] == "👍"

    def test_thumbs_down_adds_to_l4(self, tc, cache):
        """👎 on a word with a cached URL should add L4 negative entry."""
        from AnkiAI_ImageAddon.modules.cache import L1Entry
        from datetime import date
        cache.l1_store(L1Entry(
            word="broken", sense_id="", group="B",
            visual_type="photo", image_url="https://bad.example/img.png",
            clip_score=0.3, qc_verified=False, qc_rounds=0,
            source_provider="test", attribution="",
            resolved_by="rule", last_verified=date.today().isoformat(),
            flagged_for_review=False,
        ))

        tc.record(word="broken", group="B")
        tc.feedback("broken", "👎")

        assert cache.l4_is_bad("https://bad.example/img.png", "url_bad")

    def test_thumbs_down_no_url_no_crash(self, tc, cache):
        """👎 on a word without a cached URL should not crash."""
        tc.record(word="ghost", group="M")
        tc.feedback("ghost", "👎")  # no L1 entry — should not raise


# ---------------------------------------------------------------------------
# Recent entries
# ---------------------------------------------------------------------------

class TestRecentEntries:
    def test_returns_entries_for_word(self, tc):
        tc.record(word="test_word", group="A", latency_ms=500)
        tc.record(word="test_word", group="A", latency_ms=300)
        entries = tc.recent_entries("test_word", limit=2)
        assert len(entries) == 2

    def test_unknown_word_returns_empty(self, tc):
        assert tc.recent_entries("nonexistent") == []

    def test_limit_respected(self, tc):
        for i in range(10):
            tc.record(word="many", group="A", latency_ms=i * 100)
        entries = tc.recent_entries("many", limit=3)
        assert len(entries) == 3


# ---------------------------------------------------------------------------
# Adjustment suggestions
# ---------------------------------------------------------------------------

class TestSuggestAdjustments:
    def test_no_data_returns_empty(self, tc):
        assert tc.suggest_adjustments() == []

    def test_suggests_raise_clip_threshold_on_high_qc_fails(self, tc):
        """When many cards in a group need QC rounds, suggest raising threshold."""
        for _ in range(10):
            tc.record(word="abstract", group="E",
                      resolved_by="clip|gemini-vision-qc", latency_ms=3000,
                      clip_score=0.15, qc_rounds=2)
        suggestions = tc.suggest_adjustments()
        keys = [s["key"] for s in suggestions]
        assert "clip_confidence_threshold" in keys

    def test_suggests_lower_clip_threshold_on_very_low_scores(self, tc):
        """When avg CLIP score is very low, suggest lowering threshold."""
        for _ in range(10):
            tc.record(word="rare", group="D",
                      resolved_by="rule", latency_ms=1500,
                      clip_score=0.10, qc_rounds=0)
        suggestions = tc.suggest_adjustments()
        keys = [s["key"] for s in suggestions]
        assert "clip_confidence_threshold" in keys

    def test_suggests_provider_review_on_high_easy_latency(self, tc):
        """Easy group with high latency → review provider timeout."""
        for _ in range(5):
            tc.record(word="slow_apple", group="A",
                      resolved_by="rule|wikimedia", latency_ms=4000,
                      clip_score=0.8, qc_rounds=0)
        suggestions = tc.suggest_adjustments()
        keys = [s["key"] for s in suggestions]
        assert "card_latency_budget_ms" in keys

    def test_healthy_data_few_suggestions(self, tc):
        """Normal data should produce few or no suggestions."""
        tc.record(word="good", group="A", resolved_by="rule|cache",
                  latency_ms=800, clip_score=0.7, qc_rounds=0)
        tc.record(word="nice", group="C", resolved_by="rule|cache",
                  latency_ms=500, clip_score=0.9, qc_rounds=0)
        suggestions = tc.suggest_adjustments()
        # Should have no critical suggestions
        assert len(suggestions) <= 2


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_telemetry_collector(self, cache):
        reset_telemetry_collector()
        tc = get_telemetry_collector(cache_manager=cache)
        assert isinstance(tc, TelemetryCollector)
        tc2 = get_telemetry_collector()
        assert tc2 is tc
        reset_telemetry_collector()
