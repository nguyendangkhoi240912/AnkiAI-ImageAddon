"""
Quota Manager — GĐ4, G4.4                                  [MS §11]
=========================================================================
Theo dõi hạn mức AI theo ngày và phút; thực thi chuỗi giảm cấp khi cạn.

Degrade chain (MS §11.2, Chỉ thị 6):
  1. Tăng batch size (giảm số lượt gọi)
  2. Giảm tỉ lệ lấy mẫu (các bước không bắt buộc)
  3. Nhóm B → nghĩa trội theo tần suất, bỏ qua AI phân biệt nghĩa
  4. Nhóm E/F/J → tra bảng proxy tĩnh, ngừng AI sinh ẩn dụ mới
  5. Tắt hẳn AI text → rule-based + CLIP toàn bộ

Vision QC degrade (Chỉ thị 6):
  KHI quota vision cạn → bỏ QC + badge ⚠ unverified + hàng đợi nền
  KHÔNG giảm tỉ lệ lấy mẫu.

reserve_interactive: 20% hạn mức dành riêng cho luồng đơn thẻ (Editor).

Không import Qt/Anki.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from threading import Lock
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Degrade levels (tăng dần theo mức độ nghiêm trọng)
# ---------------------------------------------------------------------------

class DegradeLevel(IntEnum):
    FULL = 0         # all AI enabled
    LARGER_BATCH = 1 # step 1: increase batch size
    SKIP_OPTIONAL = 2 # step 2: skip optional AI steps
    NO_SENSE_AI = 3  # step 3: group B falls back to freq-based sense
    NO_ABSTRACT_AI = 4 # step 4: group E/F/J use static proxy table
    NO_AI = 5        # step 5: full rule+CLIP only


@dataclass
class _ModelBucket:
    """Per-model quota tracking."""
    rpd_limit: int = 14400     # requests per day
    rpm_limit: int = 30        # requests per minute
    tpm_limit: int = 6000      # tokens per minute
    rpd_used: int = 0
    rpm_window: list = field(default_factory=list)   # [(timestamp,)]
    tpm_window: list = field(default_factory=list)   # [(timestamp, tokens)]
    last_reset: float = field(default_factory=time.time)

    def _clean_windows(self) -> None:
        now = time.monotonic()
        self.rpm_window = [t for t in self.rpm_window if now - t < 60.0]
        self.tpm_window = [(t, n) for t, n in self.tpm_window if now - t < 60.0]

    def rpm_used(self) -> int:
        self._clean_windows()
        return len(self.rpm_window)

    def tpm_used(self) -> int:
        self._clean_windows()
        return sum(n for _, n in self.tpm_window)

    def can_use(self, tokens: int = 0) -> bool:
        self._clean_windows()
        if self.rpd_used >= self.rpd_limit:
            return False
        if len(self.rpm_window) >= self.rpm_limit:
            return False
        if tokens and self.tpm_used() + tokens > self.tpm_limit:
            return False
        return True

    def record(self, tokens: int = 0) -> None:
        now = time.monotonic()
        self._clean_windows()
        self.rpd_used += 1
        self.rpm_window.append(now)
        if tokens:
            self.tpm_window.append((now, tokens))

    def usage_pct(self) -> float:
        """Return fraction of daily budget consumed (0–1)."""
        if self.rpd_limit == 0:
            return 1.0
        return self.rpd_used / self.rpd_limit


class QuotaManager:
    """
    Central quota tracker and degrade decision maker.

    Usage:
        qm = QuotaManager(config)
        if qm.allow("groq_workhorse"):
            ... call API ...
            qm.record("groq_workhorse", tokens=250)
        level = qm.degrade_level()
    """

    # Default limits (overridden from config in __init__)
    _DEFAULT_LIMITS: Dict[str, Dict] = {
        "groq_workhorse": {"rpd": 14400, "rpm": 30, "tpm": 6000},
        "groq_hard":      {"rpd": 2000,  "rpm": 10, "tpm": 4000},
        "groq_vision":    {"rpd": 500,   "rpm": 10, "tpm": 2000},
        "gemini_vision":  {"rpd": 1500,  "rpm": 15, "tpm": 4000},
        "gemini_text":    {"rpd": 1500,  "rpm": 15, "tpm": 4000},
    }

    def __init__(self, config=None):
        self._lock = Lock()
        self._buckets: Dict[str, _ModelBucket] = {}
        self._reserve_pct: float = 0.20   # 20% reserved for interactive (Editor)
        self._degrade: DegradeLevel = DegradeLevel.FULL

        if config is not None:
            self._reserve_pct = config.get("reserve_interactive_quota_pct", 20) / 100.0

        # Initialise buckets from defaults
        for name, limits in self._DEFAULT_LIMITS.items():
            self._buckets[name] = _ModelBucket(
                rpd_limit=limits["rpd"],
                rpm_limit=limits["rpm"],
                tpm_limit=limits["tpm"],
            )

    # ------------------------------------------------------------------
    # Contract (MS §17.2)
    # ------------------------------------------------------------------

    def allow(self, model: str, *, interactive: bool = False, tokens: int = 0) -> bool:
        """Return True if a request for *model* is within quota.

        Args:
            model:       Key matching _DEFAULT_LIMITS (e.g. "groq_workhorse").
            interactive: If True, checks against the interactive reserve rather
                         than the batch budget.
            tokens:      Estimated tokens to pre-check against TPM.
        """
        with self._lock:
            bucket = self._buckets.get(model)
            if bucket is None:
                return True   # unknown model — allow optimistically

            # Interactive path uses reserved 20% of daily budget
            if interactive:
                reserve_rpd = int(bucket.rpd_limit * self._reserve_pct)
                # Simple check: has the interactive sub-budget been consumed?
                # (We track all usage together; reserve is just a cap)
                if bucket.rpd_used >= reserve_rpd:
                    logger.info(f"Interactive quota exhausted for {model}")
                    return False

            return bucket.can_use(tokens=tokens)

    def record(self, model: str, tokens: int = 0) -> None:
        """Record a completed API call."""
        with self._lock:
            bucket = self._buckets.get(model)
            if bucket:
                bucket.record(tokens=tokens)
        self._update_degrade()

    def degrade_level(self) -> DegradeLevel:
        """Current degrade level based on quota state across all models."""
        return self._degrade

    def is_vision_qc_available(self) -> bool:
        """Return True if vision QC (Gemini or Groq vision) has quota left."""
        with self._lock:
            gem = self._buckets.get("gemini_vision")
            grv = self._buckets.get("groq_vision")
            gem_ok = gem.can_use() if gem else True
            grv_ok = grv.can_use() if grv else False
            return gem_ok or grv_ok

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                name: {
                    "rpd_used": b.rpd_used,
                    "rpd_limit": b.rpd_limit,
                    "rpd_pct": round(b.usage_pct() * 100, 1),
                    "rpm_used": b.rpm_used(),
                    "rpm_limit": b.rpm_limit,
                }
                for name, b in self._buckets.items()
            }

    def remaining_display(self) -> str:
        """Human-readable one-liner for UI display."""
        snap = self.snapshot()
        parts = []
        for name, d in snap.items():
            pct = d["rpd_pct"]
            parts.append(f"{name}: {100-pct:.0f}% left")
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Internal: update degrade level
    # ------------------------------------------------------------------

    def _update_degrade(self) -> None:
        """Re-evaluate degrade level; escalate only (never de-escalate mid-session)."""
        with self._lock:
            wh = self._buckets.get("groq_workhorse")
            gv = self._buckets.get("gemini_vision")
            grv = self._buckets.get("groq_vision")

            wh_pct = wh.usage_pct() if wh else 0.0
            vision_ok = (gv and gv.can_use()) or (grv and grv.can_use())

            new_level = DegradeLevel.FULL

            if wh_pct >= 0.95 or not vision_ok:
                new_level = max(new_level, DegradeLevel.NO_AI)
            elif wh_pct >= 0.80:
                new_level = max(new_level, DegradeLevel.NO_ABSTRACT_AI)
            elif wh_pct >= 0.60:
                new_level = max(new_level, DegradeLevel.NO_SENSE_AI)
            elif wh_pct >= 0.40:
                new_level = max(new_level, DegradeLevel.SKIP_OPTIONAL)
            elif wh_pct >= 0.20:
                new_level = max(new_level, DegradeLevel.LARGER_BATCH)

            if new_level > self._degrade:
                logger.warning(
                    f"Quota degrade level escalated: {self._degrade.name} → {new_level.name}"
                )
                self._degrade = new_level


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_global_qm: Optional[QuotaManager] = None


def get_quota_manager(config=None) -> QuotaManager:
    global _global_qm
    if _global_qm is None:
        _global_qm = QuotaManager(config=config)
    return _global_qm
