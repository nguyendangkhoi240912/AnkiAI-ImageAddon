"""
Pipeline Accuracy-First — GĐ4, G4.5                        [MS §9, §17.2]
=========================================================================
Orchestrator toàn bộ luồng §9.1 + budget governor §9.2.

Contract (MS §17.2):
    def process_card(word: str, sentence: str, budget_ms: int) -> CardResult

Chỉ thị 1: Vision QC soi 1 ảnh/từ (ứng viên tốt nhất sau CLIP); vòng 2 soi kế tiếp.
Chỉ thị 3: Cổng vòng 2 = round2_min_remaining_ms (default 2050).
Chỉ thị 4: Batch mode → budget cấp lô; groq_batch_deadline_ms cho AI.

Không import Qt/Anki — module này phải chạy/test được độc lập.
"""
from __future__ import annotations

import dataclasses
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass (MS §17.2)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class CardResult:
    url: Optional[str]
    verified: bool            # True = passed vision QC
    qc_rounds: int            # 0 | 1 | 2
    resolved_by: str          # e.g. "rule|clip|groq-batch|gemini-vision-qc"
    flagged: bool             # True = ⚠ unverified or requires review
    latency_ms: int


# ---------------------------------------------------------------------------
# Budget governor
# ---------------------------------------------------------------------------

class _BudgetGovernor:
    """Track elapsed time; provide remaining budget; gate each step.

    Usage:
        gov = _BudgetGovernor(budget_ms=4000)
        if gov.can_afford(estimated_ms=1800):
            ...call AI...
            gov.tick()   # marks elapsed so far
    """

    def __init__(self, budget_ms: int):
        self._budget_ms = budget_ms
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0

    def remaining_ms(self) -> float:
        return self._budget_ms - self.elapsed_ms()

    def can_afford(self, estimated_ms: float) -> bool:
        return self.remaining_ms() >= estimated_ms


# ---------------------------------------------------------------------------
# Pipeline steps (time estimates per §9.2)
# ---------------------------------------------------------------------------

# Conservative estimates for remaining-budget calculations
_SEARCH_ESTIMATE_MS  = 700
_CLIP_ESTIMATE_MS    = 150
_QC_ESTIMATE_MS      = 1200
_ROUND2_RESERVE_MS   = _SEARCH_ESTIMATE_MS + _CLIP_ESTIMATE_MS + _QC_ESTIMATE_MS  # 2050


def _is_easy_group(group: str) -> bool:
    return group in ("A", "C", "I", "K", "M", "N")


def _is_hard_group(group: str) -> bool:
    return group in ("B", "D", "E", "F", "H", "J", "L")


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def process_card(
    word: str,
    sentence: str = "",
    budget_ms: int = 4000,
    *,
    config=None,
    groq=None,
    gemini=None,
    clip=None,
    quota=None,
    search_fn=None,  # callable(query, visual_type, top_n) -> list[Candidate]
) -> CardResult:
    """
    Full pipeline for one card (§9.1 + §9.2).

    Args:
        word:       Vocabulary word.
        sentence:   Context sentence from the card.
        budget_ms:  Total time budget in milliseconds.
        config:     ConfigManager (optional; for reading settings).
        groq:       GroqClient (optional; injected for testing).
        gemini:     GeminiClient (optional).
        clip:       ClipScorer (optional).
        quota:      QuotaManager (optional).
        search_fn:  Provider search function (optional).

    Returns:
        CardResult with url, verified flag, qc_rounds, resolved_by, latency_ms.
    """
    gov = _BudgetGovernor(budget_ms)

    # ------------------------------------------------------------------
    # Step 0: read config values (once)
    # ------------------------------------------------------------------
    round2_min = 2050   # ms
    clip_threshold = 0.30
    strict_mode = False

    if config is not None:
        round2_min = config.get("round2_min_remaining_ms", 2050)
        clip_threshold = config.get("clip_confidence_threshold", 0.30)
        strict_mode = config.get("strict_accuracy_mode", False)

    # ------------------------------------------------------------------
    # Step 1: Cache L1 check (placeholder — GĐ5 implements SQLite cache)
    # ------------------------------------------------------------------
    # TODO-v5: cache.lookup(word, sentence) → CardResult if hit

    # ------------------------------------------------------------------
    # Step 2: Classify (100% local)
    # ------------------------------------------------------------------
    try:
        from AnkiAI_ImageAddon.modules.classification.taxonomy import classify
        verdict = classify(word, sentence=sentence)
    except Exception as e:
        logger.error(f"Classification failed for '{word}': {e}")
        return CardResult(
            url=None, verified=False, qc_rounds=0,
            resolved_by="error", flagged=True,
            latency_ms=int(gov.elapsed_ms()),
        )

    # ------------------------------------------------------------------
    # Local SVG path (groups K, N) — 0 requests
    # ------------------------------------------------------------------
    if verdict.visual_type == "local_svg":
        try:
            from AnkiAI_ImageAddon.image_providers.local_svg_provider import get_local_svg
            cand = get_local_svg(verdict.word, verdict.group)
            if cand:
                return CardResult(
                    url=cand.url, verified=True, qc_rounds=0,
                    resolved_by="local_svg", flagged=False,
                    latency_ms=int(gov.elapsed_ms()),
                )
        except Exception as e:
            logger.warning(f"SVG generation failed for '{word}': {e}")

    # ------------------------------------------------------------------
    # Group M — no image
    # ------------------------------------------------------------------
    if verdict.group == "M":
        return CardResult(
            url=None, verified=True, qc_rounds=0,
            resolved_by="rule-skip-M", flagged=False,
            latency_ms=int(gov.elapsed_ms()),
        )

    # ------------------------------------------------------------------
    # Degrade check
    # ------------------------------------------------------------------
    from AnkiAI_ImageAddon.modules.quota import get_quota_manager, DegradeLevel
    if quota is None:
        quota = get_quota_manager(config)

    degrade = quota.degrade_level()

    # ------------------------------------------------------------------
    # Step 3: AI text (for hard groups or when CLIP confidence low)
    # ------------------------------------------------------------------
    query = verdict.query
    en_query = verdict.en_query or verdict.query
    resolved_by_parts = [verdict.resolved_by]

    # Chỉ thị 7: Group D uses AI only when candidate count < min_candidates_before_ai_expand.
    # At this stage, candidates haven't been fetched yet; we flag D as needing AI
    # by checking if the group is D and degrade allows it. The actual candidate
    # count gate is re-checked after the initial search (step 4b below).
    _min_candidates = 3
    if config is not None:
        _min_candidates = config.get("min_candidates_before_ai_expand", 3)

    needs_ai = (
        _is_hard_group(verdict.group) and
        degrade < DegradeLevel.NO_AI and
        gov.can_afford(_QC_ESTIMATE_MS + _SEARCH_ESTIMATE_MS + _CLIP_ESTIMATE_MS)
    )
    # For group D: defer AI decision until after initial search (see step 4b)
    _group_d_ai_deferred = verdict.group == "D" and needs_ai
    if _group_d_ai_deferred:
        needs_ai = False   # will be re-evaluated after search
    if needs_ai and groq is not None and quota.allow("groq_workhorse"):
        tier = "hard" if verdict.group in ("L", "F") else "workhorse"
        try:
            items = [{"word": word, "sentence": sentence, "pos": "", "lang": "en"}]
            deadline = config.get("groq_batch_deadline_ms", 8000) if config else 8000
            verdicts_ai = groq.classify_batch(items, tier=tier, deadline_ms=deadline)
            if verdicts_ai:
                v = verdicts_ai[0]
                query = v.get("q", query)
                en_query = v.get("en_query", en_query)
                resolved_by_parts.append("groq-batch")
                quota.record("groq_workhorse")
        except Exception as e:
            logger.warning(f"Groq classify failed for '{word}': {e}")

    elif needs_ai and gemini is not None and quota.allow("gemini_text"):
        try:
            items = [{"word": word, "sentence": sentence, "pos": "", "lang": "en"}]
            verdicts_ai = gemini.classify_batch(items)
            if verdicts_ai:
                v = verdicts_ai[0]
                query = v.get("q", query)
                en_query = v.get("en_query", en_query)
                resolved_by_parts.append("gemini-text")
                quota.record("gemini_text")
        except Exception as e:
            logger.warning(f"Gemini text fallback failed for '{word}': {e}")

    # ------------------------------------------------------------------
    # Step 4: Search (external providers)
    # ------------------------------------------------------------------
    candidates = []
    if search_fn is not None:
        try:
            top_n = config.get("clip_topk_candidates", 12) if config else 12
            candidates = search_fn(query, verdict.visual_type, top_n)
        except Exception as e:
            logger.warning(f"Search failed for '{word}' (query='{query}'): {e}")

    if not candidates:
        flagged = True
        return CardResult(
            url=None, verified=False, qc_rounds=0,
            resolved_by="|".join(resolved_by_parts),
            flagged=flagged,
            latency_ms=int(gov.elapsed_ms()),
        )

    # ------------------------------------------------------------------
    # Step 4b: Group D AI escalation — if too few candidates (Chỉ thị 7)
    # ------------------------------------------------------------------
    if _group_d_ai_deferred and len(candidates) < _min_candidates:
        if groq is not None and quota.allow("groq_workhorse"):
            try:
                items = [{"word": word, "sentence": sentence, "pos": "", "lang": "en"}]
                deadline = config.get("groq_batch_deadline_ms", 8000) if config else 8000
                verdicts_ai = groq.classify_batch(items, tier="workhorse", deadline_ms=deadline)
                if verdicts_ai:
                    v = verdicts_ai[0]
                    query = v.get("q", query)
                    en_query = v.get("en_query", en_query)
                    resolved_by_parts.append("groq-batch-D")
                    quota.record("groq_workhorse")
                    # Re-search with expanded query
                    if search_fn is not None:
                        top_n = config.get("clip_topk_candidates", 12) if config else 12
                        candidates = search_fn(query, verdict.visual_type, top_n) or candidates
            except Exception as e:
                logger.warning(f"Group D AI expand failed for '{word}': {e}")

    # ------------------------------------------------------------------
    # Step 5: CLIP rerank
    # ------------------------------------------------------------------
    top_candidates = candidates

    if clip is not None and gov.can_afford(_QC_ESTIMATE_MS):
        try:
            from AnkiAI_ImageAddon.modules.reranker import rerank
            top_candidates = rerank(candidates, verdict, clip)
            resolved_by_parts.append("clip")
        except Exception as e:
            logger.warning(f"CLIP rerank failed for '{word}': {e}")

    # ------------------------------------------------------------------
    # Step 6: Vision QC (synchronous, ≤2 rounds — Chỉ thị 1)
    # ------------------------------------------------------------------
    qc_rounds = 0
    best_url = top_candidates[0].url if top_candidates else None
    verified = False

    vision_available = (
        degrade < DegradeLevel.NO_AI and
        quota.is_vision_qc_available() and
        gemini is not None and
        gov.can_afford(_QC_ESTIMATE_MS)
    )

    if vision_available and best_url:
        for round_idx in range(2):   # max 2 rounds (Chỉ thị 1 + vòng 2)
            if round_idx == 1:
                # Chỉ thị 3: cổng vòng 2
                if gov.remaining_ms() < round2_min:
                    logger.debug(f"Budget insufficient for QC round 2 ({gov.remaining_ms():.0f} ms < {round2_min})")
                    break
                if len(top_candidates) < 2:
                    break
                best_url = top_candidates[round_idx].url

            pair = [{
                "i": 0,
                "word": word,
                "sense": verdict.sense_id or verdict.group,
                "group": verdict.group,
                "image_url": best_url,
            }]

            try:
                results = gemini.vision_qc_batch(pair)
                qc_rounds += 1
                quota.record("gemini_vision")

                if results and results[0].get("ok"):
                    verified = True
                    resolved_by_parts.append("gemini-vision-qc")
                    break
                else:
                    reason = results[0].get("r", "qc-failed") if results else "no-response"
                    logger.debug(f"QC round {round_idx+1} failed for '{word}': {reason}")
                    # Continue to round 2 if budget allows

            except Exception as e:
                logger.warning(f"Vision QC error for '{word}': {e}")
                break

    # ------------------------------------------------------------------
    # Step 7: Degrade outcome
    # ------------------------------------------------------------------
    if not verified:
        if strict_mode:
            # strict: return no URL, queue for background retry
            return CardResult(
                url=None, verified=False, qc_rounds=qc_rounds,
                resolved_by="|".join(resolved_by_parts) + "|strict-no-image",
                flagged=True,
                latency_ms=int(gov.elapsed_ms()),
            )
        # default: attach best candidate with ⚠ flag
        return CardResult(
            url=best_url, verified=False, qc_rounds=qc_rounds,
            resolved_by="|".join(resolved_by_parts) + "|unverified",
            flagged=True,
            latency_ms=int(gov.elapsed_ms()),
        )

    return CardResult(
        url=best_url, verified=True, qc_rounds=qc_rounds,
        resolved_by="|".join(resolved_by_parts),
        flagged=False,
        latency_ms=int(gov.elapsed_ms()),
    )
