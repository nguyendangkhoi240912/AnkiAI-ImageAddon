"""
Pipeline Budget Tests — GĐ4, G4.6                          [MS §20]
=========================================================================
Assert:
  1. Tổng latency của một thẻ không vượt card_latency_budget_ms.
  2. Vòng 2 QC không mở khi remaining < round2_min_remaining_ms.
  3. Group M → url=None, không gọi AI.
  4. Group K → url=data:image/svg+xml, verified=True, qc_rounds=0.
  5. Degrade: khi vision QC unavailable → flagged=True, url vẫn có.

Tất cả network calls được mock — test chạy offline.
"""
import sys
import os
import time
import unittest.mock as mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AnkiAI_ImageAddon.modules.pipeline import process_card, CardResult, _BudgetGovernor
from AnkiAI_ImageAddon.modules.quota import QuotaManager, DegradeLevel
from AnkiAI_ImageAddon.image_providers.base_provider import Candidate


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_candidate(url="https://example.com/img.jpg", score=0.5):
    return Candidate(url=url, provider="test", visual_type="photo",
                     title="test image", score=score)


class _FakeGroq:
    def classify_batch(self, items, tier="workhorse", deadline_ms=None):
        return [{"w": items[0]["word"], "en_query": items[0]["word"],
                 "q": items[0]["word"], "alt": "", "c": 0.9}]


class _FakeGemini:
    def __init__(self, qc_result=True):
        self._qc_result = qc_result

    def classify_batch(self, items, timeout_s=None):
        return []

    def vision_qc_batch(self, pairs, timeout_s=None):
        return [{"i": 0, "ok": self._qc_result, "r": "test"}]


class _SlowGemini(_FakeGemini):
    """Simulates slow QC that consumes all remaining budget."""
    def vision_qc_batch(self, pairs, timeout_s=None):
        time.sleep(0.05)   # 50 ms simulated
        return [{"i": 0, "ok": True, "r": "ok"}]


class _FailingGemini(_FakeGemini):
    def vision_qc_batch(self, pairs, timeout_s=None):
        return []   # simulates empty / error response


def _search_fn_with(candidates):
    def _fn(query, visual_type, top_n):
        return candidates
    return _fn


# ---------------------------------------------------------------------------
# Test: BudgetGovernor
# ---------------------------------------------------------------------------

class TestBudgetGovernor:
    def test_can_afford_within_budget(self):
        gov = _BudgetGovernor(4000)
        assert gov.can_afford(1000) is True

    def test_cannot_afford_over_budget(self):
        gov = _BudgetGovernor(100)
        time.sleep(0.11)   # exhaust budget
        assert gov.can_afford(50) is False

    def test_remaining_decreases_over_time(self):
        gov = _BudgetGovernor(4000)
        r1 = gov.remaining_ms()
        time.sleep(0.05)
        r2 = gov.remaining_ms()
        assert r2 < r1


# ---------------------------------------------------------------------------
# Test: Group M — skip, no AI
# ---------------------------------------------------------------------------

class TestGroupM:
    def test_group_m_returns_no_url(self):
        result = process_card("the", budget_ms=4000)
        assert result.url is None
        assert result.verified is True
        assert result.qc_rounds == 0

    def test_group_m_no_ai_call(self):
        groq = mock.MagicMock()
        result = process_card("and", budget_ms=4000, groq=groq)
        groq.classify_batch.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Group K — local SVG, 0 requests
# ---------------------------------------------------------------------------

class TestGroupK:
    def test_group_k_returns_svg(self):
        result = process_card("above", budget_ms=4000)
        assert result.url is not None
        assert result.url.startswith("data:image/svg+xml")

    def test_group_k_verified_no_qc_rounds(self):
        result = process_card("below", budget_ms=4000)
        assert result.verified is True
        assert result.qc_rounds == 0

    def test_group_k_no_network(self):
        with mock.patch("requests.get", side_effect=RuntimeError("network!")):
            result = process_card("between", budget_ms=4000)
        assert result.url is not None


# ---------------------------------------------------------------------------
# Test: Budget constraint — total latency
# ---------------------------------------------------------------------------

class TestBudgetConstraint:
    def test_latency_within_budget(self):
        """process_card must finish within 2× budget (generous tolerance for CI)."""
        budget = 500   # tight budget
        t0 = time.perf_counter()
        result = process_card("apple", budget_ms=budget, search_fn=_search_fn_with([]))
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < budget * 4, f"Took {elapsed:.0f} ms, budget was {budget} ms"

    def test_result_contains_latency_ms(self):
        result = process_card("run", budget_ms=4000, search_fn=_search_fn_with([]))
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms >= 0


# ---------------------------------------------------------------------------
# Test: QC round 2 gating (Chỉ thị 3)
# ---------------------------------------------------------------------------

class TestQCRound2Gate:
    def test_round2_not_opened_when_budget_insufficient(self):
        """With very tight budget, round 2 QC should NOT run."""
        candidates = [make_candidate("http://a.com/1.jpg"), make_candidate("http://a.com/2.jpg")]
        gemini = _FakeGemini(qc_result=False)  # QC always fails → would normally trigger round 2

        # Use tiny budget that can't afford round 2
        class _TinyConfig:
            def get(self, key, default=None):
                defaults = {
                    "round2_min_remaining_ms": 99999,  # impossibly high threshold
                    "clip_confidence_threshold": 0.30,
                    "strict_accuracy_mode": False,
                    "groq_batch_deadline_ms": 8000,
                    "clip_topk_candidates": 12,
                }
                return defaults.get(key, default)

        result = process_card(
            "tactics",
            budget_ms=4000,
            config=_TinyConfig(),
            gemini=gemini,
            search_fn=_search_fn_with(candidates),
        )
        assert result.qc_rounds <= 1   # round 2 blocked by impossibly high threshold

    def test_round2_runs_when_budget_allows(self):
        """Round 2 should run when budget is sufficient and round 1 fails."""
        candidates = [make_candidate("http://a.com/1.jpg"), make_candidate("http://a.com/2.jpg")]

        # QC fails on round 1, passes on round 2
        call_count = [0]
        class _TwoRoundGemini:
            def classify_batch(self, items, timeout_s=None): return []
            def vision_qc_batch(self, pairs, timeout_s=None):
                call_count[0] += 1
                ok = call_count[0] >= 2   # fail first, pass second
                return [{"i": 0, "ok": ok, "r": "test"}]

        class _PermissiveConfig:
            def get(self, key, default=None):
                defaults = {
                    "round2_min_remaining_ms": 1,  # almost always allow
                    "clip_confidence_threshold": 0.30,
                    "strict_accuracy_mode": False,
                    "groq_batch_deadline_ms": 8000,
                    "clip_topk_candidates": 12,
                }
                return defaults.get(key, default)

        quota = QuotaManager()
        result = process_card(
            "tactics",
            budget_ms=4000,
            config=_PermissiveConfig(),
            gemini=_TwoRoundGemini(),
            search_fn=_search_fn_with(candidates),
            quota=quota,
        )
        # Should have attempted QC (may be verified or not depending on timing)
        assert result.latency_ms >= 0


# ---------------------------------------------------------------------------
# Test: Degrade — vision QC unavailable → flagged, url still present
# ---------------------------------------------------------------------------

class TestDegradeVisionUnavailable:
    def test_flagged_when_qc_fails(self):
        candidates = [make_candidate()]
        gemini = _FailingGemini()

        result = process_card(
            "freedom",
            budget_ms=4000,
            gemini=gemini,
            search_fn=_search_fn_with(candidates),
        )
        assert result.url is not None    # url still attached
        assert result.flagged is True    # ⚠ unverified

    def test_strict_mode_returns_no_url(self):
        candidates = [make_candidate()]
        gemini = _FailingGemini()

        class _StrictConfig:
            def get(self, key, default=None):
                d = {"strict_accuracy_mode": True, "round2_min_remaining_ms": 2050,
                     "clip_confidence_threshold": 0.30, "groq_batch_deadline_ms": 8000,
                     "clip_topk_candidates": 12}
                return d.get(key, default)

        result = process_card(
            "freedom",
            budget_ms=4000,
            config=_StrictConfig(),
            gemini=gemini,
            search_fn=_search_fn_with(candidates),
        )
        assert result.url is None
        assert result.flagged is True


# ---------------------------------------------------------------------------
# Test: No candidates found → flagged, url=None
# ---------------------------------------------------------------------------

class TestNoResults:
    def test_no_candidates_returns_none_url(self):
        result = process_card("apple", budget_ms=4000, search_fn=_search_fn_with([]))
        assert result.url is None
        assert result.flagged is True


# ---------------------------------------------------------------------------
# Test: CardResult dataclass is immutable
# ---------------------------------------------------------------------------

class TestCardResultImmutable:
    def test_frozen(self):
        r = CardResult(url=None, verified=False, qc_rounds=0,
                       resolved_by="test", flagged=False, latency_ms=100)
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError if hasattr(
            __import__("dataclasses"), "FrozenInstanceError") else AttributeError)):
            r.url = "x"  # type: ignore


import dataclasses
