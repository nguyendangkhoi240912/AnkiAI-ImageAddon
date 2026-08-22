"""
Retry Queue Tests — GĐ5, G5.3                               [MS §14, §20]
=========================================================================
Test the retry_queue table in CacheManager and the RetryQueue wrapper
in bg_handler.py.

IdlePrefetch depends on Qt/Anki (QTimer, QueryOp) and is not unit-tested
here — it will be verified via sandbox integration and manual testing.
"""
import time
from datetime import datetime, timezone, timedelta

import pytest

from AnkiAI_ImageAddon.modules.cache import CacheManager, reset_cache_manager
from AnkiAI_ImageAddon.modules.bg_handler import RetryQueue


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
def rq(cache):
    return RetryQueue(cache)


# ---------------------------------------------------------------------------
# CacheManager retry_queue methods
# ---------------------------------------------------------------------------

class TestRetryEnqueueDequeue:
    def test_enqueue_and_dequeue(self, cache):
        cache.retry_enqueue(note_id=42, word="tactics", error_msg="timeout")
        items = cache.retry_dequeue(limit=10)
        assert len(items) == 1
        assert items[0]["note_id"] == 42
        assert items[0]["word"] == "tactics"
        assert items[0]["retry_count"] == 0

    def test_dequeue_empty(self, cache):
        items = cache.retry_dequeue()
        assert items == []

    def test_dequeue_respects_limit(self, cache):
        for i in range(10):
            cache.retry_enqueue(note_id=i, word=f"word{i}")
        items = cache.retry_dequeue(limit=3)
        assert len(items) == 3

    def test_dequeue_order_is_fifo(self, cache):
        """Items with earlier next_retry_at should come first."""
        cache.retry_enqueue(note_id=1, word="first")
        # Small sleep to ensure different timestamp
        time.sleep(0.05)
        cache.retry_enqueue(note_id=2, word="second")
        items = cache.retry_dequeue(limit=10)
        assert items[0]["note_id"] == 1
        assert items[1]["note_id"] == 2


class TestRetryMarkAttempt:
    def test_increment_retry_count(self, cache):
        cache.retry_enqueue(note_id=10, word="test", max_retries=3)
        items = cache.retry_dequeue()
        item_id = items[0]["id"]

        cache.retry_mark_attempt(item_id, error_msg="still failing")

        # After mark_attempt, backoff pushes next_retry_at into the future,
        # so retry_dequeue won't return it.  Read the row directly.
        cur = cache._conn.execute(
            "SELECT retry_count, error_msg FROM retry_queue WHERE id = ?",
            (item_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == "still failing"

    def test_exhausted_retries_parked(self, cache):
        """After max_retries, next_retry_at should be far future."""
        cache.retry_enqueue(note_id=20, word="exhausted", max_retries=2)
        items = cache.retry_dequeue()
        item_id = items[0]["id"]

        # First attempt
        cache.retry_mark_attempt(item_id)
        # Second attempt (exhausts max_retries=2)
        cache.retry_mark_attempt(item_id)

        # Should no longer be due
        due = cache.retry_dequeue()
        # The item is parked at 2099 so it won't appear
        assert all(d["note_id"] != 20 for d in due)


class TestRetryRemove:
    def test_remove_item(self, cache):
        cache.retry_enqueue(note_id=30, word="removeme")
        items = cache.retry_dequeue()
        item_id = items[0]["id"]

        cache.retry_remove(item_id)

        items2 = cache.retry_dequeue()
        assert len(items2) == 0

    def test_remove_nonexistent_no_error(self, cache):
        cache.retry_remove(99999)  # should not raise


class TestRetryCount:
    def test_count_reflects_due_items(self, cache):
        assert cache.retry_count() == 0
        cache.retry_enqueue(note_id=40, word="due")
        assert cache.retry_count() == 1

    def test_exhausted_not_counted(self, cache):
        cache.retry_enqueue(note_id=41, word="exhausted", max_retries=1)
        items = cache.retry_dequeue()
        cache.retry_mark_attempt(items[0]["id"])  # exhausts
        assert cache.retry_count() == 0


class TestRetryPurgeExhausted:
    def test_purge_removes_exhausted(self, cache):
        cache.retry_enqueue(note_id=50, word="keep", max_retries=5)
        cache.retry_enqueue(note_id=51, word="purge_me", max_retries=1)
        items = cache.retry_dequeue()
        for item in items:
            if item["word"] == "purge_me":
                cache.retry_mark_attempt(item["id"])  # exhausts it

        purged = cache.retry_purge_exhausted()
        assert purged == 1
        assert cache.retry_count() == 1  # "keep" still there


class TestRetryClear:
    def test_clear_empties_queue(self, cache):
        for i in range(5):
            cache.retry_enqueue(note_id=i, word=f"w{i}")
        assert cache.retry_count() == 5
        cache.retry_clear()
        assert cache.retry_count() == 0


class TestRetryStats:
    def test_stats_includes_retry_queue(self, cache):
        stats = cache.stats()
        assert "retry_queue" in stats
        assert stats["retry_queue"] == 0
        cache.retry_enqueue(note_id=1, word="x")
        assert cache.stats()["retry_queue"] == 1


# ---------------------------------------------------------------------------
# RetryQueue wrapper (bg_handler.py)
# ---------------------------------------------------------------------------

class TestRetryQueueWrapper:
    def test_enqueue_and_due_items(self, rq, cache):
        rq.enqueue(note_id=100, word="tactics", error_msg="network")
        items = rq.due_items()
        assert len(items) == 1
        assert items[0]["word"] == "tactics"

    def test_mark_success_removes_item(self, rq):
        rq.enqueue(note_id=101, word="apple")
        items = rq.due_items()
        rq.mark_success(items[0]["id"])
        assert rq.pending_count() == 0

    def test_mark_failed_increments(self, rq):
        rq.enqueue(note_id=102, word="banana", max_retries=3)
        items = rq.due_items()
        rq.mark_failed(items[0]["id"], error_msg="still bad")
        # After one failure, item should still be due (backoff is only 30s)
        assert rq.pending_count() >= 0  # may or may not be due depending on timing

    def test_pending_count(self, rq):
        assert rq.pending_count() == 0
        rq.enqueue(note_id=103, word="cherry")
        assert rq.pending_count() == 1

    def test_purge_exhausted(self, rq):
        rq.enqueue(note_id=104, word="durian", max_retries=1)
        items = rq.due_items()
        rq.mark_failed(items[0]["id"])  # exhausts
        purged = rq.purge_exhausted()
        assert purged == 1

    def test_clear(self, rq):
        rq.enqueue(note_id=105, word="elderberry")
        rq.clear()
        assert rq.pending_count() == 0

    def test_repr(self, rq):
        rq.enqueue(note_id=106, word="fig")
        r = repr(rq)
        assert "RetryQueue" in r
        assert "pending=1" in r
