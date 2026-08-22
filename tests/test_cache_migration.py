"""
Cache Migration Tests — GĐ5, G5.2                               [MS §12, §20]
=========================================================================
Test the one-time migration from legacy ``anki_image_cache.json`` → SQLite.

The CacheManager auto-runs migration on init if:
- ``migration.done`` does NOT exist, AND
- A legacy JSON file is found (new location ``user_files/`` first, then old root).

After successful import the tombstone file is written so migration never
runs again.  Malformed or missing JSON is handled gracefully.
"""
import json
import os

import pytest

from AnkiAI_ImageAddon.modules.cache import CacheManager, reset_cache_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEGACY_CONTENT = {
    "processed_notes": [1775901724032, 1775901724161, 1775901724034],
    "last_update": "2026-04-11T18:24:37.631809",
}


def _make_legacy_json(path, data=None):
    """Write a legacy JSON file at *path*."""
    if data is None:
        data = _LEGACY_CONTENT
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


# ---------------------------------------------------------------------------
# Migration from new location (user_files/anki_image_cache.json)
# ---------------------------------------------------------------------------

class TestMigrationFromNewLocation:
    def test_imports_processed_notes(self, tmp_path):
        """Legacy JSON at user_files/ should be imported into processed_notes."""
        legacy = tmp_path / "anki_image_cache.json"
        _make_legacy_json(legacy)

        cm = CacheManager(str(tmp_path))
        try:
            assert cm.is_note_processed(1775901724032) is True
            assert cm.is_note_processed(1775901724161) is True
            assert cm.is_note_processed(1775901724034) is True
            assert cm.is_note_processed(9999999999999) is False  # not in JSON
        finally:
            cm.close()

    def test_writes_tombstone(self, tmp_path):
        """migration.done should be created after import."""
        legacy = tmp_path / "anki_image_cache.json"
        _make_legacy_json(legacy)

        cm = CacheManager(str(tmp_path))
        try:
            assert cm.migration_done is True
            assert os.path.isfile(tmp_path / "migration.done")
        finally:
            cm.close()

    def test_idempotent_migration(self, tmp_path):
        """Running migration twice should not duplicate rows."""
        legacy = tmp_path / "anki_image_cache.json"
        _make_legacy_json(legacy)

        cm1 = CacheManager(str(tmp_path))
        cm1.close()

        # Second open — migration.done already exists, so no re-import
        cm2 = CacheManager(str(tmp_path))
        try:
            # Should still have exactly 3 entries (no duplicates)
            cur = cm2._conn.execute(
                "SELECT COUNT(*) FROM processed_notes"
            )
            assert cur.fetchone()[0] == 3
        finally:
            cm2.close()


# ---------------------------------------------------------------------------
# Migration from old location (../anki_image_cache.json)
# ---------------------------------------------------------------------------

class TestMigrationFromOldLocation:
    def test_imports_from_old_location(self, tmp_path):
        """If JSON is at the old root location, still import it."""
        # Old location: one level above user_files/
        old_root = tmp_path.parent
        legacy = old_root / "anki_image_cache.json"
        _make_legacy_json(legacy)

        try:
            cm = CacheManager(str(tmp_path))
            try:
                assert cm.is_note_processed(1775901724032) is True
                assert cm.migration_done is True
            finally:
                cm.close()
        finally:
            # Cleanup legacy file
            if legacy.exists():
                legacy.unlink()

    def test_new_location_takes_precedence(self, tmp_path):
        """If both locations exist, use the new one (user_files/)."""
        # New location
        new_legacy = tmp_path / "anki_image_cache.json"
        _make_legacy_json(new_legacy, {"processed_notes": [1], "last_update": "new"})

        # Old location (should be ignored)
        old_root = tmp_path.parent
        old_legacy = old_root / "anki_image_cache.json"
        _make_legacy_json(old_legacy, {"processed_notes": [99], "last_update": "old"})

        try:
            cm = CacheManager(str(tmp_path))
            try:
                # Should have imported from new location (note_id=1), not old (99)
                assert cm.is_note_processed(1) is True
                assert cm.is_note_processed(99) is False
            finally:
                cm.close()
        finally:
            if old_legacy.exists():
                old_legacy.unlink()


# ---------------------------------------------------------------------------
# Edge cases: missing / malformed JSON
# ---------------------------------------------------------------------------

class TestMigrationEdgeCases:
    def test_no_legacy_json_does_not_crash(self, tmp_path):
        """No legacy file → migration skipped, tombstone written, no crash."""
        cm = CacheManager(str(tmp_path))
        try:
            assert cm.migration_done is True
            assert cm.stats()["processed_notes"] == 0
        finally:
            cm.close()

    def test_malformed_json_does_not_crash(self, tmp_path):
        """Corrupt JSON → warning logged, tombstone written, no crash."""
        legacy = tmp_path / "anki_image_cache.json"
        with open(legacy, "w", encoding="utf-8") as fh:
            fh.write("{not valid json!!")

        cm = CacheManager(str(tmp_path))
        try:
            assert cm.migration_done is True
            assert cm.stats()["processed_notes"] == 0
        finally:
            cm.close()

    def test_empty_json_does_not_crash(self, tmp_path):
        """Empty JSON object → no notes imported, tombstone written."""
        legacy = tmp_path / "anki_image_cache.json"
        _make_legacy_json(legacy, {"processed_notes": [], "last_update": ""})

        cm = CacheManager(str(tmp_path))
        try:
            assert cm.migration_done is True
            assert cm.stats()["processed_notes"] == 0
        finally:
            cm.close()

    def test_legacy_without_processed_notes_key(self, tmp_path):
        """JSON missing 'processed_notes' key → handled gracefully."""
        legacy = tmp_path / "anki_image_cache.json"
        _make_legacy_json(legacy, {"last_update": "2026-01-01"})

        cm = CacheManager(str(tmp_path))
        try:
            assert cm.migration_done is True
            assert cm.stats()["processed_notes"] == 0
        finally:
            cm.close()