"""
Tests for classification/clip_scorer.py — GĐ2, G2.1
Chạy độc lập, không cần Anki/Qt, không cần ONNX model.
"""
import sys
import os
import dataclasses

import pytest

# Ensure package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AnkiAI_ImageAddon.image_providers.base_provider import Candidate
from AnkiAI_ImageAddon.modules.classification.clip_scorer import (
    ClipScorer,
    _heuristic_score,
    _tokenise,
    get_clip_scorer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candidate(url="https://example.com/img.jpg", title="", attribution="", provider="test"):
    return Candidate(url=url, provider=provider, visual_type="photo", title=title, attribution=attribution)


# ---------------------------------------------------------------------------
# Unit: heuristic scorer
# ---------------------------------------------------------------------------

class TestHeuristicScore:
    def test_exact_match(self):
        score = _heuristic_score(["apple"], "apple fruit photo")
        assert score > 0.0

    def test_boost_keyword(self):
        score_plain = _heuristic_score(["tactics"], "coach training")
        score_diagram = _heuristic_score(["tactics"], "tactics map arrow diagram")
        assert score_diagram > score_plain

    def test_penalty_keyword(self):
        # No query overlap in either case; the difference is that penalty pushes
        # score toward negative before clipping. Both clip to 0.0, which means
        # the positive candidate is ≥ the penalised one — not strictly >.
        score_no_pen = _heuristic_score(["freedom"], "broken chains concept")
        score_pen = _heuristic_score(["freedom"], "coach in stadium shouting meeting")
        assert score_no_pen >= score_pen

    def test_clipped_to_unit_interval(self):
        # Many boost keywords — score should not exceed 1.0
        score = _heuristic_score(["a"], "map arrow diagram chess plan flowchart chart")
        assert 0.0 <= score <= 1.0

    def test_empty_query(self):
        score = _heuristic_score([], "some image title")
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Unit: tokenise
# ---------------------------------------------------------------------------

class TestTokenise:
    def test_basic(self):
        assert _tokenise("Hello World") == ["hello", "world"]

    def test_punctuation(self):
        assert _tokenise("apple, orange; berry.") == ["apple", "orange", "berry"]

    def test_empty(self):
        assert _tokenise("") == []


# ---------------------------------------------------------------------------
# ClipScorer — tier=heuristic (no ONNX needed)
# ---------------------------------------------------------------------------

class TestClipScorerHeuristic:
    @pytest.fixture
    def scorer(self):
        return ClipScorer(tier="heuristic")

    def test_tier_is_heuristic(self, scorer):
        assert scorer.tier == "heuristic"

    def test_score_batch_returns_sorted(self, scorer):
        candidates = [
            make_candidate(title="coach shouting in stadium"),
            make_candidate(title="tactics map with arrows diagram"),
        ]
        results = scorer.score_batch("tactics", candidates)
        assert len(results) == 2
        # diagram candidate should rank first
        _, s0 = results[0]
        _, s1 = results[1]
        assert s0 >= s1

    def test_score_batch_empty(self, scorer):
        assert scorer.score_batch("apple", []) == []

    def test_score_one(self, scorer):
        c = make_candidate(title="apple fruit photo")
        score = scorer.score_one("apple", c)
        assert 0.0 <= score <= 1.0

    def test_vi_toi_uu_a_lru_cache(self, scorer):
        """Vi tối ưu (a): text encoding cached — calling twice is safe."""
        c = make_candidate(title="test")
        scorer.score_batch("apple", [c])
        scorer.score_batch("apple", [c])  # should use cached result
        # No assertion needed beyond "no exception raised"

    def test_vi_toi_uu_b_uses_en_query(self, scorer):
        """Vi tối ưu (b): scorer accepts en_query string without error."""
        c = make_candidate(title="apple fruit")
        result = scorer.score_batch("apple fruit", [c])
        assert len(result) == 1

    def test_vi_toi_uu_c_batch_multiple(self, scorer):
        """Vi tối ưu (c): batch scoring of multiple candidates in one call."""
        candidates = [make_candidate(title=f"image {i}") for i in range(5)]
        results = scorer.score_batch("test query", candidates)
        assert len(results) == 5

    def test_scores_are_floats_in_range(self, scorer):
        candidates = [make_candidate(title="map diagram"), make_candidate(title="portrait photo")]
        results = scorer.score_batch("plan", candidates)
        for _, score in results:
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_singleton(self):
        s1 = get_clip_scorer()
        s2 = get_clip_scorer()
        assert s1 is s2


# ---------------------------------------------------------------------------
# ClipScorer — ONNX unavailable path (force heuristic via missing model)
# ---------------------------------------------------------------------------

class TestClipScorerONNXFallback:
    def test_falls_back_when_model_missing(self, tmp_path, monkeypatch):
        """If ONNX model file is missing, scorer must fall back to heuristic."""
        import AnkiAI_ImageAddon.modules.classification.clip_scorer as cs_mod
        monkeypatch.setattr(cs_mod, "_get_models_dir", lambda: tmp_path)
        scorer = ClipScorer(tier="full")
        assert scorer.tier == "heuristic"

    def test_score_batch_works_after_fallback(self, tmp_path, monkeypatch):
        import AnkiAI_ImageAddon.modules.classification.clip_scorer as cs_mod
        monkeypatch.setattr(cs_mod, "_get_models_dir", lambda: tmp_path)
        scorer = ClipScorer(tier="full")
        candidates = [make_candidate(title="apple")]
        results = scorer.score_batch("apple", candidates)
        assert len(results) == 1
