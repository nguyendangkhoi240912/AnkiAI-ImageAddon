"""
Telemetry Collector — GĐ5, G5.4                             [MS §15]
=========================================================================
Higher-level telemetry logic on top of CacheManager's raw tables.

CacheManager stores raw per-card records in the ``telemetry`` table.
This module adds:

1. ``TelemetryCollector`` — convenience wrapper for recording and querying.
2. ``suggest_adjustments()`` — periodic aggregation that analyses recent
   telemetry and returns config-key suggestions (e.g. raise
   ``clip_confidence_threshold`` if QC fail rate is high for a group).

All data stays local (``cache.sqlite``); nothing is sent externally.

Không import Qt/Anki — pure Python.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Thresholds for generating suggestions
# ---------------------------------------------------------------------------

_QC_FAIL_RATE_WARN = 0.30     # if >30% of a group's cards fail QC
_LOW_CLIP_AVG_WARN = 0.20     # if avg clip_score < 0.20 for a group
_HIGH_LATENCY_WARN = 3500     # if avg latency_ms > 3500 for easy groups
_LOW_CACHE_HIT_WARN = 0.40    # if <40% of cards resolved by cache


class TelemetryCollector:
    """Convenience wrapper around CacheManager telemetry methods.

    Usage::

        tc = TelemetryCollector(cache_manager)
        tc.record(word="tactics", group="F", resolved_by="clip|qc", latency_ms=2800)
        suggestions = tc.suggest_adjustments(since_days=7)
    """

    def __init__(self, cache_manager):
        self._cm = cache_manager

    # -- recording --------------------------------------------------------

    def record(
        self,
        word: str,
        group: str = "",
        visual_type: str = "",
        resolved_by: str = "",
        latency_ms: int = 0,
        clip_score: float = 0.0,
        qc_rounds: int = 0,
    ) -> None:
        """Record a per-card telemetry entry."""
        self._cm.telemetry_record(
            word=word, group=group, visual_type=visual_type,
            resolved_by=resolved_by, latency_ms=latency_ms,
            clip_score=clip_score, qc_rounds=qc_rounds,
        )

    def feedback(self, word: str, vote: str) -> None:
        """Record 👍/👎 for the most recent entry of *word*."""
        self._cm.telemetry_feedback(word, vote)
        # 👎 also goes to L4 negative cache if a URL is known
        if vote in ("👎", "thumbs_down", "down"):
            hit = self._cm.l1_lookup(word)
            if hit and hit.image_url:
                self._cm.l4_add(hit.image_url, kind="url_bad",
                                reason="user_thumbs_down")

    # -- querying ---------------------------------------------------------

    def summary(self, since_days: int = 7) -> List[Dict[str, Any]]:
        """Aggregate telemetry for the last N days."""
        return self._cm.telemetry_summary(since_days=since_days)

    def recent_entries(self, word: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the N most recent telemetry rows for *word*."""
        with self._cm._lock:
            cur = self._cm._conn.execute(
                "SELECT timestamp, group_, visual_type, resolved_by, "
                "latency_ms, clip_score, qc_rounds, user_feedback "
                "FROM telemetry WHERE word = ? "
                "ORDER BY id DESC LIMIT ?",
                (word, limit),
            )
            rows = cur.fetchall()
        return [
            {
                "timestamp": r[0], "group": r[1], "visual_type": r[2],
                "resolved_by": r[3], "latency_ms": r[4],
                "clip_score": r[5], "qc_rounds": r[6],
                "user_feedback": r[7],
            }
            for r in rows
        ]

    # -- adjustment suggestions -------------------------------------------

    def suggest_adjustments(self, since_days: int = 7) -> List[Dict[str, Any]]:
        """Analyse recent telemetry and return config adjustment suggestions.

        Each suggestion is a dict:
            ``{"key": str, "current": any, "suggested": any, "reason": str}``

        This is advisory only — the caller (UI / config) decides whether
        to apply.
        """
        rows = self.summary(since_days=since_days)
        if not rows:
            return []

        suggestions: List[Dict[str, Any]] = []

        # 1. QC fail rate per group
        group_qc = self._aggregate_qc_fail_rate(rows)
        for grp, fail_rate in group_qc.items():
            if fail_rate > _QC_FAIL_RATE_WARN and grp not in ("M",):
                suggestions.append({
                    "key": "clip_confidence_threshold",
                    "current": None,
                    "suggested": "raise by 0.05",
                    "reason": (
                        f"Group {grp}: {fail_rate:.0%} of cards needed "
                        f">1 QC round (threshold >{_QC_FAIL_RATE_WARN:.0%})"
                    ),
                })

        # 2. Low CLIP score average per group
        for row in rows:
            grp = row.get("group", "")
            avg_clip = row.get("avg_clip_score", 1.0)
            if avg_clip < _LOW_CLIP_AVG_WARN and grp:
                suggestions.append({
                    "key": "clip_confidence_threshold",
                    "current": None,
                    "suggested": "lower by 0.05",
                    "reason": (
                        f"Group {grp}: avg CLIP score {avg_clip:.2f} "
                        f"is very low (below {_LOW_CLIP_AVG_WARN})"
                    ),
                })

        # 3. High latency for easy groups
        easy_groups = {"A", "C", "I", "K", "N"}
        for row in rows:
            grp = row.get("group", "")
            avg_lat = row.get("avg_latency_ms", 0)
            if grp in easy_groups and avg_lat > _HIGH_LATENCY_WARN:
                suggestions.append({
                    "key": "card_latency_budget_ms",
                    "current": None,
                    "suggested": "review easy-group provider timeout",
                    "reason": (
                        f"Group {grp}: avg latency {avg_lat:.0f} ms "
                        f"exceeds {_HIGH_LATENCY_WARN} ms for an easy group"
                    ),
                })

        # 4. Cache hit rate
        cache_hits = sum(r.get("count", 0) for r in rows
                         if "cache" in r.get("resolved_by", ""))
        total = sum(r.get("count", 0) for r in rows)
        if total > 20 and (cache_hits / total) < _LOW_CACHE_HIT_WARN:
            suggestions.append({
                "key": "idle_prefetch_enabled",
                "current": None,
                "suggested": "true",
                "reason": (
                    f"Only {cache_hits}/{total} cards resolved from cache "
                    f"(<{_LOW_CACHE_HIT_WARN:.0%}); idle prefetch could help"
                ),
            })

        return suggestions

    # -- internal ---------------------------------------------------------

    @staticmethod
    def _aggregate_qc_fail_rate(
        rows: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Compute per-group rate of cards needing >0 QC rounds."""
        group_total: Dict[str, int] = {}
        group_qc_fail: Dict[str, int] = {}
        for row in rows:
            grp = row.get("group", "")
            cnt = row.get("count", 0)
            group_total[grp] = group_total.get(grp, 0) + cnt
            # If the resolved_by contains "qc" it needed QC rounds
            if "qc" in row.get("resolved_by", "").lower():
                group_qc_fail[grp] = group_qc_fail.get(grp, 0) + cnt

        result = {}
        for grp, total in group_total.items():
            if total > 0:
                result[grp] = group_qc_fail.get(grp, 0) / total
        return result

    def __repr__(self) -> str:
        return f"<TelemetryCollector>"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_global_tc: Optional[TelemetryCollector] = None


def get_telemetry_collector(cache_manager=None) -> TelemetryCollector:
    """Return the global TelemetryCollector singleton."""
    global _global_tc
    if _global_tc is None:
        if cache_manager is None:
            from .cache import get_cache_manager
            cache_manager = get_cache_manager()
        _global_tc = TelemetryCollector(cache_manager)
    return _global_tc


def reset_telemetry_collector() -> None:
    """Discard the global singleton (for tests)."""
    global _global_tc
    _global_tc = None
