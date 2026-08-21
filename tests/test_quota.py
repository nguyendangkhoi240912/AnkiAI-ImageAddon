"""
Quota Manager Tests — GĐ4, theo WORKLOG Chỉ thị 8           [MS §11]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from AnkiAI_ImageAddon.modules.quota import QuotaManager, DegradeLevel


class TestQuotaManager:
    @pytest.fixture
    def qm(self):
        return QuotaManager()

    def test_allow_initially(self, qm):
        assert qm.allow("groq_workhorse") is True

    def test_degrade_level_starts_full(self, qm):
        assert qm.degrade_level() == DegradeLevel.FULL

    def test_record_increments_usage(self, qm):
        qm.record("groq_workhorse", tokens=100)
        snap = qm.snapshot()
        assert snap["groq_workhorse"]["rpd_used"] == 1

    def test_exhausted_bucket_disallows(self, qm):
        bucket = qm._buckets["groq_workhorse"]
        bucket.rpd_used = bucket.rpd_limit
        assert qm.allow("groq_workhorse") is False

    def test_vision_qc_available_initially(self, qm):
        assert qm.is_vision_qc_available() is True

    def test_vision_qc_unavailable_when_gemini_exhausted(self, qm):
        for b in ["gemini_vision", "groq_vision"]:
            bucket = qm._buckets[b]
            bucket.rpd_used = bucket.rpd_limit
        assert qm.is_vision_qc_available() is False

    def test_degrade_escalates_when_workhorse_near_limit(self, qm):
        bucket = qm._buckets["groq_workhorse"]
        # Drive to 80% usage
        bucket.rpd_used = int(bucket.rpd_limit * 0.80)
        qm._update_degrade()
        assert qm.degrade_level() >= DegradeLevel.NO_ABSTRACT_AI

    def test_degrade_no_ai_when_fully_exhausted(self, qm):
        bucket = qm._buckets["groq_workhorse"]
        bucket.rpd_used = bucket.rpd_limit
        qm._update_degrade()
        assert qm.degrade_level() == DegradeLevel.NO_AI

    def test_snapshot_contains_all_models(self, qm):
        snap = qm.snapshot()
        for key in ["groq_workhorse", "groq_hard", "gemini_vision"]:
            assert key in snap

    def test_remaining_display_is_string(self, qm):
        assert isinstance(qm.remaining_display(), str)

    def test_unknown_model_allowed(self, qm):
        assert qm.allow("unknown_model_xyz") is True

    def test_interactive_reserve_blocks_when_exhausted(self, qm):
        bucket = qm._buckets["groq_workhorse"]
        # Use up the 20% interactive reserve
        reserve = int(bucket.rpd_limit * 0.20)
        bucket.rpd_used = reserve
        assert qm.allow("groq_workhorse", interactive=True) is False
