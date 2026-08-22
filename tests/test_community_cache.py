"""
Community Cache Tests — GĐ6, G6.1                          [MS §12, §20]
=========================================================================
Test anonymous export/import of L1/L2 cache entries.

Rules from MS §12:
  - Pack is anonymous: only word, sense_id, group, visual_type, url,
    clip_score, source_provider, attribution.  No sentence examples or
    user-identifying data.
  - Local data always wins on conflict.
  - Import is opt-in (config key ``community_cache_enabled``).
  - Pack version mismatch → skip.
"""
import json
import os
from datetime import date

import pytest

from AnkiAI_ImageAddon.modules.cache import CacheManager, L1Entry, L2Entry


@pytest.fixture
def cache(tmp_path):
    user_files = tmp_path / "user_files"
    user_files.mkdir(exist_ok=True)
    cm = CacheManager(str(user_files))
    yield cm
    cm.close()


def _add_l1(cache, word, sense_id="", group="A", visual_type="photo",
            url="https://ex.com/img.png", clip_score=0.5, provider="wikimedia",
            attribution="CC BY-SA"):
    cache.l1_store(L1Entry(
        word=word, sense_id=sense_id, group=group,
        visual_type=visual_type, image_url=url,
        clip_score=clip_score, qc_verified=True, qc_rounds=1,
        source_provider=provider, attribution=attribution,
        resolved_by="rule|clip|qc", last_verified=date.today().isoformat(),
        flagged_for_review=False,
    ))


def _add_l2(cache, word, sense_id="", group="A", visual_type="photo",
            query="test query", en_query="test"):
    cache.l2_store(L2Entry(
        word=word, sense_id=sense_id, group=group,
        visual_type=visual_type, query=query, en_query=en_query,
    ))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestCommunityExport:
    def test_export_empty_cache(self, cache):
        pack = cache.community_export()
        assert pack["l1_count"] == 0
        assert pack["l2_count"] == 0
        assert pack["l1"] == []
        assert pack["l2"] == []

    def test_export_contains_l1_entries(self, cache):
        _add_l1(cache, "apple", group="A", url="https://ex.com/apple.png")
        _add_l1(cache, "tactics", sense_id="mil", group="F",
                visual_type="diagram_or_map", url="https://ex.com/map.png")
        pack = cache.community_export()
        assert pack["l1_count"] == 2
        words = {e["word"] for e in pack["l1"]}
        assert "apple" in words
        assert "tactics" in words

    def test_export_is_anonymous(self, cache):
        """Export must NOT contain sentence examples or user data."""
        _add_l1(cache, "secret_word", group="E")
        pack = cache.community_export()
        entry = pack["l1"][0]
        # These fields should be present
        for key in ("word", "sense_id", "group", "visual_type", "url",
                    "clip_score", "qc_verified", "source_provider", "attribution"):
            assert key in entry, f"Missing anonymous field: {key}"
        # These should NOT be present
        assert "sentence" not in entry
        assert "user_feedback" not in entry
        assert "note_id" not in entry
        assert "last_verified" not in entry

    def test_export_contains_l2_entries(self, cache):
        _add_l2(cache, "break", sense_id="verb", query="break fracture")
        pack = cache.community_export()
        assert pack["l2_count"] == 1
        assert pack["l2"][0]["query"] == "break fracture"

    def test_export_pack_version(self, cache):
        pack = cache.community_export()
        assert pack["version"] == CacheManager._COMMUNITY_PACK_VERSION
        assert "exported_at" in pack

    def test_export_to_file(self, cache, tmp_path):
        _add_l1(cache, "file_test", group="A")
        out_path = str(tmp_path / "pack.json")
        count = cache.community_export_to_file(out_path)
        assert count == 1
        assert os.path.isfile(out_path)
        with open(out_path, "r") as f:
            data = json.load(f)
        assert data["l1_count"] == 1


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

class TestCommunityImport:
    def test_import_l1_entries(self, cache):
        pack = {
            "version": 1,
            "l1": [{"word": "imported", "sense_id": "", "group": "A",
                     "visual_type": "photo", "url": "https://ex.com/imp.png",
                     "clip_score": 0.7, "qc_verified": True,
                     "source_provider": "pixabay", "attribution": ""}],
            "l2": [],
        }
        result = cache.community_import(pack)
        assert result["l1_imported"] == 1
        hit = cache.l1_lookup("imported")
        assert hit is not None
        assert hit.image_url == "https://ex.com/imp.png"
        assert hit.resolved_by == "community"

    def test_import_l2_entries(self, cache):
        pack = {
            "version": 1,
            "l1": [],
            "l2": [{"word": "imported_l2", "sense_id": "", "group": "B",
                     "visual_type": "photo", "query": "imported query",
                     "en_query": "imported"}],
        }
        result = cache.community_import(pack)
        assert result["l2_imported"] == 1
        hit = cache.l2_lookup("imported_l2")
        assert hit is not None
        assert hit.query == "imported query"

    def test_local_wins_on_conflict(self, cache):
        """If local L1 entry exists, import should skip it."""
        _add_l1(cache, "local_word", group="A", url="https://local/img.png",
                clip_score=0.9, provider="local")
        pack = {
            "version": 1,
            "l1": [{"word": "local_word", "sense_id": "", "group": "A",
                     "visual_type": "photo", "url": "https://remote/img.png",
                     "clip_score": 0.1, "qc_verified": False,
                     "source_provider": "remote", "attribution": ""}],
            "l2": [],
        }
        result = cache.community_import(pack)
        assert result["l1_imported"] == 0
        hit = cache.l1_lookup("local_word")
        assert hit.image_url == "https://local/img.png"  # unchanged
        assert hit.clip_score == pytest.approx(0.9)       # unchanged

    def test_version_mismatch_skips(self, cache):
        pack = {"version": 99, "l1": [{"word": "bad_version"}], "l2": []}
        result = cache.community_import(pack)
        assert result["l1_imported"] == 0

    def test_empty_word_skipped(self, cache):
        pack = {"version": 1, "l1": [{"word": "", "url": "https://x"}], "l2": []}
        result = cache.community_import(pack)
        assert result["l1_imported"] == 0

    def test_import_from_file(self, cache, tmp_path):
        _add_l1(cache, "existing", group="A")
        pack = cache.community_export()
        out_path = str(tmp_path / "pack.json")
        with open(out_path, "w") as f:
            json.dump(pack, f)

        # Create a fresh cache and import
        user_files2 = tmp_path / "user_files2"
        user_files2.mkdir(exist_ok=True)
        cm2 = CacheManager(str(user_files2))
        try:
            result = cm2.community_import_from_file(out_path)
            assert result["l1_imported"] == 1
            hit = cm2.l1_lookup("existing")
            assert hit is not None
            assert hit.resolved_by == "community"
        finally:
            cm2.close()

    def test_import_from_bad_file(self, cache, tmp_path):
        bad_path = str(tmp_path / "bad.json")
        with open(bad_path, "w") as f:
            f.write("{not valid json!!")
        result = cache.community_import_from_file(bad_path)
        assert result["l1_imported"] == 0

    def test_import_from_missing_file(self, cache):
        result = cache.community_import_from_file("/nonexistent/path.json")
        assert result["l1_imported"] == 0


# ---------------------------------------------------------------------------
# Round-trip: export → import
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_export_then_import_preserves_data(self, cache, tmp_path):
        _add_l1(cache, "roundtrip", sense_id="noun", group="B",
                visual_type="photo", url="https://ex.com/rt.png",
                clip_score=0.65, provider="wikimedia", attribution="CC BY")
        _add_l2(cache, "roundtrip", sense_id="noun", group="B",
                visual_type="photo", query="roundtrip test", en_query="roundtrip")

        pack = cache.community_export()

        # Import into a fresh cache
        user_files2 = tmp_path / "user_files2"
        user_files2.mkdir(exist_ok=True)
        cm2 = CacheManager(str(user_files2))
        try:
            result = cm2.community_import(pack)
            assert result["l1_imported"] == 1
            assert result["l2_imported"] == 1

            hit = cm2.l1_lookup("roundtrip", "noun")
            assert hit is not None
            assert hit.image_url == "https://ex.com/rt.png"
            assert hit.clip_score == pytest.approx(0.65)
            assert hit.resolved_by == "community"

            l2_hit = cm2.l2_lookup("roundtrip", "noun")
            assert l2_hit is not None
            assert l2_hit.query == "roundtrip test"
        finally:
            cm2.close()
