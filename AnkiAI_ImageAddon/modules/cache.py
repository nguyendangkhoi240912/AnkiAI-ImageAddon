"""
Cache Manager — GĐ5, G5.1                                    [MS §12]
=========================================================================
SQLite 4-tier cache with WAL mode, JSON importer, and migration tombstone.

Layers:
    L1  word → final URL (instant lookup for repeated words)
    L2  word + sense → visual_query (permanent, saves re-classification)
    L3  query → candidate URL list (30-day TTL)
    L4  negative cache: bad URLs / bad proxies (learned from QC failures & 👎)

Plus a ``telemetry`` table for per-card processing records (§15).

Rules:
    - Data lives in ``user_files/`` (the only dir Anki preserves across updates).
    - SQLite from day one — no JSON backend dual-path.
    - Migration: if cache.sqlite is missing but anki_image_cache.json exists
      (at new or old location) → import once → write ``migration.done``.
    - Thread-safe (threading.Lock); WAL mode for concurrent reads.
    - Pure Python — must NOT import Qt / Anki.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
import sqlite3
import time
from datetime import date, datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CACHE_DIR_NAME = "user_files"
_DB_FILENAME = "cache.sqlite"
_MIGRATION_TOMBSTONE = "migration.done"
_LEGACY_JSON_NEW = "anki_image_cache.json"          # inside user_files/
_LEGACY_JSON_OLD = "../anki_image_cache.json"        # old root position (relative)

_L3_DEFAULT_TTL_DAYS = 30

# Schema version — bump when tables change
_SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Data-classes returned by lookups
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class L1Entry:
    """Result of an L1 cache hit."""
    word: str
    sense_id: str
    group: str
    visual_type: str
    image_url: str
    clip_score: float
    qc_verified: bool
    qc_rounds: int
    source_provider: str
    attribution: str
    resolved_by: str
    last_verified: str      # ISO date
    flagged_for_review: bool


@dataclasses.dataclass(frozen=True)
class L2Entry:
    """word + sense → visual_query (saves re-classification)."""
    word: str
    sense_id: str
    group: str
    visual_type: str
    query: str
    en_query: str


@dataclasses.dataclass(frozen=True)
class L3Entry:
    """query → candidate URL list (time-limited)."""
    query: str
    urls_json: str           # JSON array of URLs
    expires: str             # ISO date


@dataclasses.dataclass(frozen=True)
class L4Entry:
    """Negative cache entry."""
    key: str                 # URL or proxy name
    kind: str                # 'url_bad' | 'proxy_bad'
    reason: str
    created: str             # ISO date


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys  = ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- L1: word → final image URL
CREATE TABLE IF NOT EXISTS cache_l1 (
    word              TEXT NOT NULL,
    sense_id          TEXT NOT NULL DEFAULT '',
    group_            TEXT NOT NULL DEFAULT '',
    visual_type       TEXT NOT NULL DEFAULT '',
    image_url         TEXT NOT NULL,
    clip_score        REAL   NOT NULL DEFAULT 0.0,
    qc_verified       INTEGER NOT NULL DEFAULT 0,
    qc_rounds         INTEGER NOT NULL DEFAULT 0,
    source_provider   TEXT NOT NULL DEFAULT '',
    attribution       TEXT NOT NULL DEFAULT '',
    resolved_by       TEXT NOT NULL DEFAULT '',
    last_verified     TEXT NOT NULL DEFAULT '',
    flagged_for_review INTEGER NOT NULL DEFAULT 0,
    created           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    PRIMARY KEY (word, sense_id)
);
CREATE INDEX IF NOT EXISTS idx_l1_word ON cache_l1(word);

-- L2: word + sense → visual_query (permanent)
CREATE TABLE IF NOT EXISTS cache_l2 (
    word        TEXT NOT NULL,
    sense_id    TEXT NOT NULL DEFAULT '',
    group_      TEXT NOT NULL DEFAULT '',
    visual_type TEXT NOT NULL DEFAULT '',
    query       TEXT NOT NULL DEFAULT '',
    en_query    TEXT NOT NULL DEFAULT '',
    created     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    PRIMARY KEY (word, sense_id)
);
CREATE INDEX IF NOT EXISTS idx_l2_word ON cache_l2(word);

-- L3: query → candidate URLs (30-day TTL)
CREATE TABLE IF NOT EXISTS cache_l3 (
    query       TEXT PRIMARY KEY,
    urls_json   TEXT NOT NULL DEFAULT '[]',
    expires     TEXT NOT NULL,
    created     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
CREATE INDEX IF NOT EXISTS idx_l3_query ON cache_l3(query);

-- L4: negative cache
CREATE TABLE IF NOT EXISTS cache_l4 (
    key         TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'url_bad',
    reason      TEXT NOT NULL DEFAULT '',
    created     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    PRIMARY KEY (key, kind)
);

-- Telemetry (MS §15): per-card processing record
CREATE TABLE IF NOT EXISTS telemetry (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    word          TEXT NOT NULL,
    group_        TEXT NOT NULL DEFAULT '',
    visual_type   TEXT NOT NULL DEFAULT '',
    resolved_by   TEXT NOT NULL DEFAULT '',
    latency_ms    INTEGER NOT NULL DEFAULT 0,
    clip_score    REAL NOT NULL DEFAULT 0.0,
    qc_rounds     INTEGER NOT NULL DEFAULT 0,
    user_feedback TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_word ON telemetry(word);

-- Processed-note IDs (imported from legacy JSON)
CREATE TABLE IF NOT EXISTS processed_notes (
    note_id     INTEGER PRIMARY KEY,
    imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);
"""


# ---------------------------------------------------------------------------
# CacheManager
# ---------------------------------------------------------------------------

class CacheManager:
    """SQLite-backed 4-tier cache.

    Thread-safe: all public methods acquire ``self._lock`` before touching
    the database.  The connection is created with ``check_same_thread=False``
    and WAL journal mode so concurrent readers do not block each other.

    Usage::

        cm = CacheManager("/path/to/user_files")
        hit = cm.l1_lookup("tactics")
        if hit is None:
            ...  # run pipeline
            cm.l1_store(entry)
    """

    def __init__(self, user_files_dir: str):
        self._dir = user_files_dir
        self._db_path = os.path.join(user_files_dir, _DB_FILENAME)
        self._tombstone = os.path.join(user_files_dir, _MIGRATION_TOMBSTONE)
        self._lock = Lock()

        os.makedirs(user_files_dir, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._open()
        self._run_migration()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _open(self) -> None:
        """Open (or create) the SQLite database and apply DDL."""
        conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            timeout=10,
        )
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_DDL)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
            (str(_SCHEMA_VERSION),),
        )
        conn.commit()
        self._conn = conn

    def close(self) -> None:
        """Close the database connection (safe to call multiple times)."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    # ------------------------------------------------------------------
    # Migration from legacy JSON
    # ------------------------------------------------------------------

    def _run_migration(self) -> None:
        """One-time import of legacy ``anki_image_cache.json`` → SQLite.

        Runs only when:
        - ``migration.done`` does NOT exist, AND
        - A legacy JSON file is found at the new or old location.

        After successful import the tombstone file is written so the
        migration never runs again.
        """
        if os.path.exists(self._tombstone):
            return

        json_path = self._find_legacy_json()
        if json_path is None:
            # Nothing to import — still write tombstone so we don't scan again
            self._write_tombstone()
            return

        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Legacy cache JSON unread (%s): %s", json_path, exc)
            self._write_tombstone()
            return

        imported = 0
        with self._lock:
            # Import processed_notes list (the only data the legacy cache holds)
            note_ids = data.get("processed_notes", [])
            for nid in note_ids:
                try:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO processed_notes(note_id) VALUES (?)",
                        (int(nid),),
                    )
                    imported += 1
                except (ValueError, sqlite3.IntegrityError):
                    pass

            self._conn.commit()

        logger.info(
            "Legacy cache migration: imported %d processed_note IDs from %s",
            imported, json_path,
        )
        self._write_tombstone()

    def _find_legacy_json(self) -> Optional[str]:
        """Return path to legacy JSON if found, else None."""
        # Check new location first (user_files/)
        new_path = os.path.join(self._dir, _LEGACY_JSON_NEW)
        if os.path.isfile(new_path):
            return new_path

        # Check old location (repo root, one level above user_files/)
        old_path = os.path.normpath(os.path.join(self._dir, _LEGACY_JSON_OLD))
        if os.path.isfile(old_path):
            return old_path

        return None

    def _write_tombstone(self) -> None:
        """Write the migration.done marker."""
        try:
            with open(self._tombstone, "w", encoding="utf-8") as fh:
                fh.write(
                    f"Migration completed at {datetime.now(timezone.utc).isoformat()}\n"
                )
        except OSError as exc:
            logger.warning("Could not write migration tombstone: %s", exc)

    @property
    def migration_done(self) -> bool:
        return os.path.exists(self._tombstone)

    # ------------------------------------------------------------------
    # L1: word → final URL
    # ------------------------------------------------------------------

    def l1_lookup(self, word: str, sense_id: str = "") -> Optional[L1Entry]:
        """Return cached L1 entry or None."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT word, sense_id, group_, visual_type, image_url, "
                "clip_score, qc_verified, qc_rounds, source_provider, "
                "attribution, resolved_by, last_verified, flagged_for_review "
                "FROM cache_l1 WHERE word = ? AND sense_id = ?",
                (word, sense_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return L1Entry(
            word=row[0], sense_id=row[1], group=row[2], visual_type=row[3],
            image_url=row[4], clip_score=row[5], qc_verified=bool(row[6]),
            qc_rounds=row[7], source_provider=row[8], attribution=row[9],
            resolved_by=row[10], last_verified=row[11],
            flagged_for_review=bool(row[12]),
        )

    def l1_lookup_any_sense(self, word: str) -> List[L1Entry]:
        """Return all L1 entries for a word (any sense)."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT word, sense_id, group_, visual_type, image_url, "
                "clip_score, qc_verified, qc_rounds, source_provider, "
                "attribution, resolved_by, last_verified, flagged_for_review "
                "FROM cache_l1 WHERE word = ?",
                (word,),
            )
            rows = cur.fetchall()
        results = []
        for r in rows:
            results.append(L1Entry(
                word=r[0], sense_id=r[1], group=r[2], visual_type=r[3],
                image_url=r[4], clip_score=r[5], qc_verified=bool(r[6]),
                qc_rounds=r[7], source_provider=r[8], attribution=r[9],
                resolved_by=r[10], last_verified=r[11],
                flagged_for_review=bool(r[12]),
            ))
        return results

    def l1_store(self, entry: L1Entry) -> None:
        """Insert or replace an L1 entry."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache_l1 "
                "(word, sense_id, group_, visual_type, image_url, clip_score, "
                "qc_verified, qc_rounds, source_provider, attribution, "
                "resolved_by, last_verified, flagged_for_review) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.word, entry.sense_id, entry.group, entry.visual_type,
                    entry.image_url, entry.clip_score, int(entry.qc_verified),
                    entry.qc_rounds, entry.source_provider, entry.attribution,
                    entry.resolved_by, entry.last_verified,
                    int(entry.flagged_for_review),
                ),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # L2: word + sense → visual_query
    # ------------------------------------------------------------------

    def l2_lookup(self, word: str, sense_id: str = "") -> Optional[L2Entry]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT word, sense_id, group_, visual_type, query, en_query "
                "FROM cache_l2 WHERE word = ? AND sense_id = ?",
                (word, sense_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return L2Entry(
            word=row[0], sense_id=row[1], group=row[2],
            visual_type=row[3], query=row[4], en_query=row[5],
        )

    def l2_store(self, entry: L2Entry) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache_l2 "
                "(word, sense_id, group_, visual_type, query, en_query) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (entry.word, entry.sense_id, entry.group,
                 entry.visual_type, entry.query, entry.en_query),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # L3: query → candidate URLs (TTL)
    # ------------------------------------------------------------------

    def l3_lookup(self, query: str) -> Optional[List[str]]:
        """Return list of cached URLs if not expired, else None."""
        today = date.today().isoformat()
        with self._lock:
            cur = self._conn.execute(
                "SELECT urls_json, expires FROM cache_l3 WHERE query = ?",
                (query,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        urls_json, expires = row
        if expires < today:
            return None  # expired
        try:
            return json.loads(urls_json)
        except json.JSONDecodeError:
            return None

    def l3_store(
        self,
        query: str,
        urls: List[str],
        ttl_days: int = _L3_DEFAULT_TTL_DAYS,
    ) -> None:
        """Store candidate URLs with a TTL."""
        from datetime import timedelta
        expires = (date.today() + timedelta(days=ttl_days)).isoformat()
        urls_json = json.dumps(urls, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache_l3 (query, urls_json, expires) "
                "VALUES (?, ?, ?)",
                (query, urls_json, expires),
            )
            self._conn.commit()

    def l3_purge_expired(self) -> int:
        """Remove expired L3 rows; return count deleted."""
        today = date.today().isoformat()
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM cache_l3 WHERE expires < ?", (today,),
            )
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # L4: negative cache
    # ------------------------------------------------------------------

    def l4_is_bad(self, key: str, kind: str = "url_bad") -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT 1 FROM cache_l4 WHERE key = ? AND kind = ?",
                (key, kind),
            )
            return cur.fetchone() is not None

    def l4_add(self, key: str, kind: str = "url_bad", reason: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache_l4 (key, kind, reason) "
                "VALUES (?, ?, ?)",
                (key, kind, reason),
            )
            self._conn.commit()

    def l4_remove(self, key: str, kind: str = "url_bad") -> None:
        """Remove a negative entry (e.g. user overrides a 👎)."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM cache_l4 WHERE key = ? AND kind = ?",
                (key, kind),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Telemetry (MS §15)
    # ------------------------------------------------------------------

    def telemetry_record(
        self,
        word: str,
        group: str = "",
        visual_type: str = "",
        resolved_by: str = "",
        latency_ms: int = 0,
        clip_score: float = 0.0,
        qc_rounds: int = 0,
        user_feedback: str = "",
    ) -> None:
        """Write one telemetry row."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO telemetry "
                "(word, group_, visual_type, resolved_by, latency_ms, "
                "clip_score, qc_rounds, user_feedback) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (word, group, visual_type, resolved_by,
                 latency_ms, clip_score, qc_rounds, user_feedback),
            )
            self._conn.commit()

    def telemetry_summary(
        self, since_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Aggregate telemetry for the last N days."""
        cutoff = (
            datetime.now(timezone.utc)
            - __import__("datetime").timedelta(days=since_days)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        with self._lock:
            cur = self._conn.execute(
                "SELECT group_, visual_type, resolved_by, "
                "COUNT(*) as cnt, "
                "AVG(latency_ms) as avg_lat, "
                "AVG(clip_score) as avg_clip "
                "FROM telemetry WHERE timestamp >= ? "
                "GROUP BY group_, visual_type, resolved_by "
                "ORDER BY cnt DESC",
                (cutoff,),
            )
            rows = cur.fetchall()
        return [
            {
                "group": r[0], "visual_type": r[1], "resolved_by": r[2],
                "count": r[3], "avg_latency_ms": round(r[4], 1),
                "avg_clip_score": round(r[5], 3),
            }
            for r in rows
        ]

    def telemetry_feedback(
        self, word: str, feedback: str
    ) -> None:
        """Record 👍/👎 for the most recent telemetry row of *word*."""
        with self._lock:
            self._conn.execute(
                "UPDATE telemetry SET user_feedback = ? "
                "WHERE id = (SELECT MAX(id) FROM telemetry WHERE word = ?)",
                (feedback, word),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Processed notes (imported from legacy JSON)
    # ------------------------------------------------------------------

    def is_note_processed(self, note_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT 1 FROM processed_notes WHERE note_id = ?",
                (note_id,),
            )
            return cur.fetchone() is not None

    def mark_note_processed(self, note_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO processed_notes(note_id) VALUES (?)",
                (note_id,),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Stats & diagnostics
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        """Return row counts for every table."""
        with self._lock:
            result = {}
            for table in (
                "cache_l1", "cache_l2", "cache_l3", "cache_l4",
                "telemetry", "processed_notes",
            ):
                cur = self._conn.execute(
                    f"SELECT COUNT(*) FROM {table}"  # safe: table names are hardcoded
                )
                result[table] = cur.fetchone()[0]
        return result

    # ------------------------------------------------------------------
    # Pipeline integration helper
    # ------------------------------------------------------------------

    def lookup_card(
        self, word: str, sense_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Convenience: L1 hit → dict compatible with pipeline.CardResult fields.

        Returns None on miss.  Callers can construct a CardResult from the dict.
        """
        entry = self.l1_lookup(word, sense_id)
        if entry is None:
            return None
        return {
            "url": entry.image_url,
            "verified": entry.qc_verified,
            "qc_rounds": entry.qc_rounds,
            "resolved_by": entry.resolved_by + "|cache",
            "flagged": entry.flagged_for_review,
        }

    def store_card_result(
        self,
        word: str,
        sense_id: str,
        group: str,
        visual_type: str,
        image_url: str,
        clip_score: float = 0.0,
        qc_verified: bool = False,
        qc_rounds: int = 0,
        source_provider: str = "",
        attribution: str = "",
        resolved_by: str = "",
        flagged: bool = False,
    ) -> None:
        """Store a pipeline result into L1 + L2 (if url is not None)."""
        if not image_url:
            return

        today = date.today().isoformat()
        self.l1_store(L1Entry(
            word=word, sense_id=sense_id, group=group, visual_type=visual_type,
            image_url=image_url, clip_score=clip_score,
            qc_verified=qc_verified, qc_rounds=qc_rounds,
            source_provider=source_provider, attribution=attribution,
            resolved_by=resolved_by, last_verified=today,
            flagged_for_review=flagged,
        ))

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def vacuum(self) -> None:
        """Run VACUUM to reclaim space."""
        with self._lock:
            self._conn.execute("VACUUM")

    def __repr__(self) -> str:
        return f"<CacheManager db={self._db_path!r}>"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_global_cm: Optional[CacheManager] = None


def get_cache_manager(user_files_dir: Optional[str] = None) -> CacheManager:
    """Return the global CacheManager singleton.

    On first call, *user_files_dir* must be provided (typically from
    ``__init__.py`` or ``pipeline.py``).  Subsequent calls may omit it.
    """
    global _global_cm
    if _global_cm is None:
        if user_files_dir is None:
            # Auto-detect: assume this file is modules/cache.py → parent/user_files/
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            user_files_dir = os.path.join(addon_dir, _CACHE_DIR_NAME)
        _global_cm = CacheManager(user_files_dir)
    return _global_cm


def reset_cache_manager() -> None:
    """Close and discard the global singleton (for tests)."""
    global _global_cm
    if _global_cm is not None:
        _global_cm.close()
    _global_cm = None
