"""
Tests for modules/reranker.py — GĐ2, G2.2
Chạy độc lập, không cần Anki/Qt.
"""
import sys
import os
import dataclasses

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AnkiAI_ImageAddon.image_providers.base_provider import Candidate
from AnkiAI_ImageAddon.modules.reranker import rerank, _compute_bias


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candidate(url="https://example.com/img.jpg", title="", attribution="", provider="test", score=0.0):
    return Candidate(url=url, provider=provider, visual_type="photo",
                     title=title, attribution=attribution, score=score)


class FakeVerdict:
    def __init__(self, group="A", en_query=""):
        self.group = group
        self.en_query = en_query
        self.query = en_query


class FakeClipScorer:
    """Returns fixed scores by index for deterministic testing."""
    def __init__(self, scores):
        self._scores = scores

    def score_batch(self, en_query, candidates):
        return [(c, self._scores[i]) for i, c in enumerate(candidates)]


# ---------------------------------------------------------------------------
# _compute_bias
# ---------------------------------------------------------------------------

class TestComputeBias:
    def test_boost_for_diagram_keywords_group_f(self):
        c = make_candidate(title="tactics map with arrows diagram chess plan")
        bias = _compute_bias(c, "F")
        assert bias > 0

    def test_penalty_for_bad_keywords_group_f(self):
        c = make_candidate(title="coach shouting in stadium meeting suit")
        bias = _compute_bias(c, "F")
        assert bias < 0

    def test_neutral_group_a(self):
        """Group A gets half the bias multiplier."""
        c_diag = make_candidate(title="map arrow diagram")
        c_coach = make_candidate(title="coach stadium")
        bias_a_diag = _compute_bias(c_diag, "A")
        bias_f_diag = _compute_bias(c_diag, "F")
        # Group A bias is exactly half of group F bias
        assert abs(bias_a_diag - bias_f_diag * 0.5) < 1e-9


# ---------------------------------------------------------------------------
# rerank
# ---------------------------------------------------------------------------

class TestRerank:
    def test_empty_candidates(self):
        result = rerank([], FakeVerdict(), None)
        assert result == []

    def test_sorted_by_combined_score(self):
        c1 = make_candidate(url="http://a.com/1.jpg", title="coach shouting")
        c2 = make_candidate(url="http://a.com/2.jpg", title="tactics map diagram arrows")
        clip = FakeClipScorer([0.3, 0.3])  # equal CLIP; bias should differentiate
        verdict = FakeVerdict(group="F", en_query="tactics")
        ranked = rerank([c1, c2], verdict, clip)
        assert ranked[0].url == c2.url  # diagram should win for group F

    def test_returns_new_candidates_with_score(self):
        c = make_candidate(title="apple fruit")
        clip = FakeClipScorer([0.7])
        ranked = rerank([c], FakeVerdict(group="A", en_query="apple"), clip)
        assert len(ranked) == 1
        # score should be updated (Candidate is frozen; must be new instance)
        assert ranked[0].score != c.score  # new Candidate with combined score

    def test_frozen_original_not_mutated(self):
        """Original Candidate must stay frozen/unmutated."""
        c = make_candidate(title="test", score=0.0)
        clip = FakeClipScorer([0.5])
        rerank([c], FakeVerdict(group="A", en_query="test"), clip)
        assert c.score == 0.0  # original unchanged

    def test_without_clip(self):
        """clip=None → heuristic-only, should still return sorted list."""
        c1 = make_candidate(url="http://a.com/1.jpg", title="coach stadium")
        c2 = make_candidate(url="http://a.com/2.jpg", title="tactics map diagram")
        ranked = rerank([c1, c2], FakeVerdict(group="F", en_query="tactics"), clip=None)
        assert len(ranked) == 2
        # No assertion on order since clip=None yields 0.0 clip_scores;
        # result depends on bias alone which should prefer diagram.
        assert ranked[0].url == c2.url

    def test_clip_failure_degrades_gracefully(self):
        """If clip.score_batch raises, reranker should not crash."""
        class BrokenClip:
            def score_batch(self, q, cands):
                raise RuntimeError("ONNX session crashed")

        c = make_candidate(title="apple")
        ranked = rerank([c], FakeVerdict(group="A", en_query="apple"), BrokenClip())
        assert len(ranked) == 1

    def test_scores_are_in_unit_interval(self):
        candidates = [make_candidate(title=f"img {i}") for i in range(8)]
        clip = FakeClipScorer([i * 0.1 for i in range(8)])
        ranked = rerank(candidates, FakeVerdict(group="A", en_query="test"), clip)
        for c in ranked:
            assert 0.0 <= c.score <= 1.0

    def test_regression_tactics(self):
        """Regression test: 'tactics' group F — diagram/map must beat coach photo."""
        coach = make_candidate(url="http://a.com/coach.jpg",
                               title="football coach shouting at players in stadium")
        map_img = make_candidate(url="http://a.com/map.jpg",
                                 title="military tactics map with attack arrows")
        clip = FakeClipScorer([0.4, 0.4])  # equal CLIP scores
        ranked = rerank([coach, map_img], FakeVerdict(group="F", en_query="tactics"), clip)
        assert ranked[0].url == map_img.url, (
            "Tactics regression: map/diagram image should outrank coach photo"
        )


# ---------------------------------------------------------------------------
# Integration: ClipScorer + reranker
# ---------------------------------------------------------------------------

class TestClipRerankerIntegration:
    def test_heuristic_clip_plus_reranker(self):
        from AnkiAI_ImageAddon.modules.classification.clip_scorer import ClipScorer
        scorer = ClipScorer(tier="heuristic")
        candidates = [
            make_candidate(url="http://a.com/1.jpg", title="coach shouting stadium"),
            make_candidate(url="http://a.com/2.jpg", title="tactics military map arrows"),
        ]
        verdict = FakeVerdict(group="F", en_query="tactics")
        ranked = rerank(candidates, verdict, scorer)
        assert len(ranked) == 2
        assert ranked[0].url == "http://a.com/2.jpg"
