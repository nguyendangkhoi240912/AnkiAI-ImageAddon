"""
Reranker — GĐ2, G2.2                                       [MS §8, §17.2]
=========================================================================
CLIP-gate + bias scoring theo nhóm từ, thực hiện "4 lớp chốt tactics" lớp 3.

Contract (MS §17.2):
    def rerank(candidates: list[Candidate], verdict: Verdict, clip) -> list[Candidate]

Quy tắc bias (MS §8, mục 3):
  • Nhóm F (diagram_or_map) — cộng điểm cho từ khoá:
      map, arrow, diagram, chess, plan, flowchart, chart, graph,
      blueprint, schema, structure, process, workflow, strategy,
      infographic, vector, illustration
  • Nhóm F — trừ điểm cho:
      coach, stadium, whistle, shouting, suit, meeting,
      portrait, headshot, selfie

Ngoài nhóm F, bias được áp nhẹ hơn (×0.5) để không làm lệch nhóm ảnh thông thường.

Không import Qt/Anki.
"""
from __future__ import annotations

import dataclasses
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bias keyword tables
# ---------------------------------------------------------------------------
_BOOST_KEYWORDS = frozenset({
    "map", "arrow", "diagram", "chess", "plan", "flowchart", "chart", "graph",
    "blueprint", "schema", "structure", "process", "workflow", "strategy",
    "infographic", "vector", "illustration",
})

_PENALTY_KEYWORDS = frozenset({
    "coach", "stadium", "whistle", "shouting", "suit", "meeting",
    "portrait", "headshot", "selfie",
})

# Bias magnitudes
_BOOST_PER_KEYWORD = 0.15
_PENALTY_PER_KEYWORD = 0.20

# Weight mixing: clip_score × w_clip + bias × w_bias
_W_CLIP_DEFAULT = 0.70
_W_BIAS_DEFAULT = 0.30
# For group F the bias weight is higher — we really want diagrams, not photos
_W_CLIP_GROUP_F = 0.50
_W_BIAS_GROUP_F = 0.50


def _tokenise(text: str) -> List[str]:
    return re.findall(r"[a-z]+", text.lower())


def _compute_bias(candidate, group: str) -> float:
    """Return a bias score in [−1, 1] for the candidate given the word group.

    Uses candidate.title and candidate.attribution as text sources.
    """
    cand_text = f"{candidate.title} {candidate.attribution} {candidate.provider}"
    tokens = set(_tokenise(cand_text))

    boost = sum(_BOOST_PER_KEYWORD for t in tokens if t in _BOOST_KEYWORDS)
    penalty = sum(_PENALTY_PER_KEYWORD for t in tokens if t in _PENALTY_KEYWORDS)

    # Non-F groups get half the bias influence so normal photo search is not distorted
    multiplier = 1.0 if group == "F" else 0.5
    return (boost - penalty) * multiplier


def rerank(
    candidates: List,       # list[Candidate]
    verdict,                # Verdict
    clip,                   # ClipScorer | None
    *,
    clip_weight: float = _W_CLIP_DEFAULT,
    bias_weight: float = _W_BIAS_DEFAULT,
) -> List:
    """Rerank candidates using CLIP score + group bias.

    Args:
        candidates: Unordered list of Candidate objects (from provider search).
        verdict:    Verdict returned by taxonomy classifier.  Uses verdict.en_query
                    for CLIP text encoding (MS §10 vi-tối ưu b) and verdict.group
                    for bias weight selection.
        clip:       ClipScorer instance, or None → heuristic-only rerank.
        clip_weight: Weight given to CLIP score (0–1).
        bias_weight: Weight given to bias score (0–1).

    Returns:
        New list of Candidate objects (frozen dataclasses replaced via
        dataclasses.replace) sorted descending by combined score.
    """
    if not candidates:
        return []

    group = getattr(verdict, "group", "A")
    en_query = getattr(verdict, "en_query", None) or getattr(verdict, "query", "")

    # Adjust weights for group F
    if group == "F":
        clip_weight = _W_CLIP_GROUP_F
        bias_weight = _W_BIAS_GROUP_F

    # CLIP scores
    clip_scores: List[float]
    if clip is not None:
        try:
            clip_results = clip.score_batch(en_query, candidates)
            # clip_results is [(candidate, score), ...] sorted desc
            # Build a lookup by candidate index
            score_map = {id(c): s for c, s in clip_results}
            clip_scores = [score_map.get(id(c), 0.0) for c in candidates]
        except Exception as e:
            logger.warning(f"CLIP scoring failed ({e}), using 0.0 for all candidates")
            clip_scores = [0.0] * len(candidates)
    else:
        clip_scores = [0.0] * len(candidates)

    # Combine CLIP + bias
    scored = []
    for c, cs in zip(candidates, clip_scores):
        bias = _compute_bias(c, group)
        # Normalise bias to [0, 1] (raw bias in roughly [−0.5, 0.5+])
        bias_norm = max(0.0, min(1.0, (bias + 0.5)))
        combined = clip_weight * cs + bias_weight * bias_norm
        # Candidate is frozen; create new instance with updated score
        new_c = dataclasses.replace(c, score=round(combined, 6))
        scored.append(new_c)

    scored.sort(key=lambda c: c.score, reverse=True)
    logger.debug(
        f"rerank: group={group}, top={scored[0].url!r} score={scored[0].score:.4f}"
        if scored else "rerank: no candidates"
    )
    return scored
