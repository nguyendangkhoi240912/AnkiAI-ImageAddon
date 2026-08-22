"""
Cache Tests — GĐ5, G5.2                                      [MS §12, §20]
=========================================================================
Test SQLite 4-tier cache read/write, WAL mode, TTL expiry, and crash resilience.

All tests use isolated temp databases via pytest tmp_path fixture.
"""
import json
import os
import sqlite3
import time
from datetime import date, timedelta

import pytest

from AnkiAI_ImageAddon.modules.cache import (
    CacheManager,
    L1Entry,
    L2Entry,
    L3Entry,
    L4Entry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cache(tmp_path):
    """Provide a fresh CacheManager backed by a temp directory."""
    user_files = tmp_path / "user_files"
    user_files.mkdir(exist_ok=True)
    cm = CacheManager(str(user_files))
    yield cm
    cm.close()


# ---------------------------------------------------------------------------
# L1: word → final URL
# ---------------------------------------------------------------------------

class TestL1Basic:
    def test_store_and_lookup(self, cache):
        entry = L1Entry(
            word="tactics", sense_id="military-strategy", group="F",
            visual_type="diagram_or_map", image_url="https://example.com/map.png",
            clip_score=0.31, qc_verified=True, qc_rounds=1,
            source_provider="wikimedia", attribution="CC BY-SA",
            resolved_by="groq-batch|clip|gemini-vision-qc",
            last_verified=date.today().isoformat(),
            flagged_for_review=False,
        )
        cache.l1_store(entry)

        hit = cache.l1_lookup("tactics", "military-strategy")
        assert hit is not None
        assert hit.image_url == "https://example.com/map.png"
        assert hit.qc_verified is True
        assert hit.clip_score == pytest.approx(0.31)

    def test_lookup_miss_returns_none(self, cache):
        assert cache.l1_lookup("nonexistent") is None

    def test_lookup_any_sense(self, cache):
        # Store two senses for same word
        cache.l1_store(L1Entry(
            word="record", sense_id="noun-audio", group="B",
            visual_type="photo", image_url="https://ex.com/vinyl.png",
            clip_score=0.8, qc_verified=True, qc_rounds=0,
            source_provider="pixabay", attribution="",
            resolved_by="rule", last_verified=date.today().isoformat(),
            flagged_for_review=False,
        ))
        cache.l1_store(L1Entry(
            word="record", sense_id="verb-write", group="G",
            visual_type="icon", image_url="https://ex.com/pencil.svg",
            clip_score=0.6, qc_verified=False, qc_rounds=0,
            source_provider="local_svg", attribution="",
            resolved_by="rule", last_verified=date.today().isoformat(),
            flagged_for_review=False,
        ))

        hits = cache.l1_lookup_any_sense("record")
        assert len(hits) == 2

    def test_replace_existing(self, cache):
        """INSERT OR REPLACE should update, not duplicate."""
        cache.l1_store(L1Entry(
            word="apple", sense_id="", group="A",
            visual_type="photo", image_url="https://ex.com/old.png",
            clip_score=0.5, qc_verified=False, qc_rounds=0,
            source_provider="pixabay", attribution="",
            resolved_by="rule", last_verified="2026-01-01",
            flagged_for_review=False,
        ))
        cache.l1_store(L1Entry(
            word="apple", sense_id="", group="A",
            visual_type="photo", image_url="https://ex.com/new.png",
            clip_score=0.9, qc_verified=True, qc_rounds=1,
            source_provider="wikimedia", attribution="CC BY",
            resolved_by="clip|gemini-vision-qc", last_verified="2026-08-22",
            flagged_for_review=False,
        ))

        hit = cache.l1_lookup("apple")
        assert hit is not None
        assert hit.image_url == "https://ex.com/new.png"
        assert hit.clip_score == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# L2: word + sense → visual_query
# ---------------------------------------------------------------------------

class TestL2Basic:
    def test_store_and_lookup(self, cache):
        entry = L2Entry(
            word="break", sense_id="verb-fracture", group="G",
            visual_type="photo", query="break fracture crack",
            en_query="break fracture",
        )
        cache.l2_store(entry)

        hit = cache.l2_lookup("break", "verb-fracture")
        assert hit is not None
        assert hit.query == "break fracture crack"
        assert hit.en_query == "break fracture"

    def test_lookup_miss(self, cache):
        assert cache.l2_lookup("unknown") is None


# ---------------------------------------------------------------------------
# L3: query → candidate URLs (TTL)
# ---------------------------------------------------------------------------

class TestL3TTL:
    def test_store_and_lookup(self, cache):
        cache.l3_store("tactical map", ["https://a.png", "https://b.png"], ttl_days=30)

        result = cache.l3_lookup("tactical map")
        assert result is not None
        assert len(result) == 2
        assert result[0] == "https://a.png"

    def test_expired_returns_none(self, cache):
        """Manually insert an already-expired row."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        urls_json = json.dumps(["https://expired.png"])
        cache._conn.execute(
            "INSERT INTO cache_l3 (query, urls_json, expires) VALUES (?, ?, ?)",
            ("old query", urls_json, yesterday),
        )
        cache._conn.commit()

        assert cache.l3_lookup("old query") is None

    def test_purge_expired(self, cache):
        """Purge should delete expired rows and return count."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        cache._conn.execute(
            "INSERT INTO cache_l3 (query, urls_json, expires) VALUES (?, '[]', ?)",
            ("q1", yesterday),
        )
        cache._conn.execute(
            "INSERT INTO cache_l3 (query, urls_json, expires) VALUES (?, '[]', ?)",
            ("q2", yesterday),
        )
        cache._conn.execute(
            "INSERT INTO cache_l3 (query, urls_json, expires) VALUES (?, '[]', ?)",
            ("q3", tomorrow),
        )
        cache._conn.commit()

        deleted = cache.l3_purge_expired()
        assert deleted == 2
        assert cache.l3_lookup("q3") == []


# ---------------------------------------------------------------------------
# L4: negative cache
# ---------------------------------------------------------------------------

class TestL4Negative:
    def test_add_and_check(self, cache):
        cache.l4_add("https://bad.png", kind="url_bad", reason="QC failed")
        assert cache.l4_is_bad("https://bad.png", "url_bad") is True

    def test_not_bad_returns_false(self, cache):
        assert cache.l4_is_bad("https://good.png") is False

    def test_remove(self, cache):
        cache.l4_add("https://bad.png", kind="url_bad", reason="QC failed")
        cache.l4_remove("https://bad.png", "url_bad")
        assert cache.l4_is_bad("https://bad.png", "url_bad") is False


# ---------------------------------------------------------------------------
# Telemetry (§15)
# ---------------------------------------------------------------------------

class TestTelemetry:
    def test_record_and_summary(self, cache):
        cache.telemetry_record(
            word="tactics", group="F", visual_type="diagram_or_map",
            resolved_by="groq-batch|clip", latency_ms=2500,
            clip_score=0.31, qc_rounds=1,
        )
        cache.telemetry_record(
            word="freedom", group="E", visual_type="metaphor_photo",
            resolved_by="rule|clip", latency_ms=800,
            clip_score=0.45, qc_rounds=0,
        )

        summary = cache.telemetry_summary(since_days=7)
        assert len(summary) >= 1
        # Most frequent first
        assert summary[0]["count"] >= 1

    def test_feedback(self, cache):
        cache.telemetry_record(word="apple", group="A", visual_type="photo")
        cache.telemetry_feedback("apple", "👎")

        # Check last row has feedback
        cur = cache._conn.execute(
            "SELECT user_feedback FROM telemetry WHERE word = 'apple' ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "👎"


# ---------------------------------------------------------------------------
# Processed notes
# ---------------------------------------------------------------------------

class TestProcessedNotes:
    def test_mark_and_check(self, cache):
        assert cache.is_note_processed(12345) is False
        cache.mark_note_processed(12345)
        assert cache.is_note_processed(12345) is True

    def test_duplicate_ignored(self, cache):
        """INSERT OR IGNORE should not raise on duplicate."""
        cache.mark_note_processed(12345)
        cache.mark_note_processed(12345)  # should not raise
        assert cache.is_note_processed(12345) is True


# ---------------------------------------------------------------------------
# Stats & helpers
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_returns_counts(self, cache):
        stats = cache.stats()
        assert "cache_l1" in stats
        assert "cache_l2" in stats
        assert "cache_l3" in stats
        assert "cache_l4" in stats
        assert "telemetry" in stats
        assert "processed_notes" in stats
        assert all(isinstance(v, int) for v in stats.values())

    def test_lookup_card_helper(self, cache):
        """lookup_card should return dict for pipeline integration."""
        cache.l1_store(L1Entry(
            word="tactics", sense_id="", group="F",
            visual_type="diagram_or_map", image_url="https://ex.com/map.png",
            clip_score=0.31, qc_verified=True, qc_rounds=1,
            source_provider="wikimedia", attribution="CC BY-SA",
            resolved_by="groq-batch|clip", last_verified=date.today().isoformat(),
            flagged_for_review=False,
        ))

        result = cache.lookup_card("tactics")
        assert result is not None
        assert result["url"] == "https://ex.com/map.png"
        assert result["verified"] is True
        assert result["resolved_by"].endswith("|cache")

    def test_store_card_result(self, cache):
        """store_card_result should write to L1."""
        cache.store_card_result(
            word="tactics", sense_id="military", group="F",
            visual_type="diagram_or_map", image_url="https://ex.com/map.png",
            qc_verified=True, qc_rounds=1,
            source_provider="wikimedia", resolved_by="clip|qc",
        )

        hit = cache.l1_lookup("tactics", "military")
        assert hit is not None
        assert hit.image_url == "https://ex.com/map.png"

    def test_store_card_result_no_url_skips(self, cache):
        """Should not write anything if url is None."""
        cache.store_card_result(
            word="nothing", sense_id="", group="M",
            visual_type="skip", image_url="",
        )
        assert cache.l1_lookup("nothing") is None


# ---------------------------------------------------------------------------
# WAL mode & crash resilience
# ---------------------------------------------------------------------------

class TestWALAndCrashResilience:
    def test_wal_mode_enabled(self, cache):
        """Database should be in WAL journal mode."""
        cur = cache._conn.execute("PRAGMA journal_mode")
        mode = cur.fetchone()[0]
        assert mode == "wal"

    def test_write_survives_close_reopen(self, tmp_path):
        """Data should persist across close/reopen cycles."""
        user_files = tmp_path / "user_files"
        user_files.mkdir(exist_ok=True)
        db_path = user_files / "cache.sqlite"

        cm = CacheManager(str(user_files))
        cm.l1_store(L1Entry(
            word="persistent", sense_id="", group="A",
            visual_type="photo", image_url="https://ex.com/img.png",
            clip_score=0.5, qc_verified=False, qc_rounds=0,
            source_provider="pixabay", attribution="",
            resolved_by="rule", last_verified=date.today().isoformat(),
            flagged_for_review=False,
        ))
        cm.close()

        # Reopen
        cm2 = CacheManager(str(user_files))
        hit = cm2.l1_lookup("persistent")
        assert hit is not None
        assert hit.image_url == "https://ex.com/img.png"
        cm2.close()

    def test_mid_write_crash_no_corruption(self, tmp_path):
        """Simulate crash mid-write: partial data should be rolled back."""
        user_files = tmp_path / "user_files"
        user_files.mkdir(exist_ok=True)

        cm = CacheManager(str(user_files))

        # Start a transaction but don't commit (simulate crash)
        cm._conn.execute(
            "INSERT INTO cache_l1 (word, sense_id, group_, image_url) "
            "VALUES ('crash_test', '', 'A', 'https://bad.png')",
        )
        # Force close without commit
        cm._conn.close()

        # Reopen — the uncommitted row should NOT be there
        cm2 = CacheManager(str(user_files))
        hit = cm2.l1_lookup("crash_test")
        assert hit is None  # rolled back
        cm2.close()


# ---------------------------------------------------------------------------
# Vacuum
# ---------------------------------------------------------------------------

class TestVacuum:
    def test_vacuum_does_not_raise(self, cache):
        """VACUUM should run without error."""
        cache.vacuum()  # should not raise
