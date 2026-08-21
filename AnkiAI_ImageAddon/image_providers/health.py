"""
HealthBoard — GĐ2, G2.6                                    [MS §4, §17.2]
=========================================================================
Theo dõi độ trễ và tỉ lệ thành công của từng provider theo thời gian thực,
quyết định thứ tự fallback động.

Contract (MS §17.2):
    class HealthBoard:
        def report(self, provider: str, latency_s: float, ok: bool) -> None
        def order(self, providers: list[str]) -> list[str]

Thuật toán:
  • Mỗi provider duy trì một EMA (Exponential Moving Average) của độ trễ
    và một EMA của tỉ lệ thành công (success_rate).
  • `order()` sắp xếp danh sách provider đầu vào theo score cao nhất trước.
  • score = success_ema / (latency_ema + ε)   → provider nhanh + ít lỗi = điểm cao.
  • Provider chưa từng được gọi nhận điểm mặc định (trung tính).
  • Provider bị coi là "down" (success_ema < down_threshold) bị đẩy xuống cuối.

Không import Qt/Anki — module này phải chạy/test độc lập.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants (không hardcode trong logic — có thể override qua kwargs)
# ---------------------------------------------------------------------------
_DEFAULT_ALPHA = 0.2          # EMA smoothing factor (smaller = slower adaptation)
_DEFAULT_LATENCY_INIT = 1.0   # seconds — assumed latency for unseen providers
_DEFAULT_SUCCESS_INIT = 0.8   # assumed success rate for unseen providers
_DOWN_THRESHOLD = 0.20        # success_ema below this → provider "down"
_EPSILON = 1e-6               # avoid division by zero


@dataclass
class _ProviderStats:
    latency_ema: float = _DEFAULT_LATENCY_INIT
    success_ema: float = _DEFAULT_SUCCESS_INIT
    call_count: int = 0
    last_call_ts: float = field(default_factory=time.time)

    @property
    def score(self) -> float:
        """Higher is better: fast + reliable."""
        return self.success_ema / (self.latency_ema + _EPSILON)

    @property
    def is_down(self) -> bool:
        return self.success_ema < _DOWN_THRESHOLD


class HealthBoard:
    """
    Thread-safe provider health tracker.

    Example:
        hb = HealthBoard()
        t0 = time.perf_counter()
        try:
            result = provider.search(...)
            hb.report(provider.name, time.perf_counter() - t0, ok=True)
        except Exception:
            hb.report(provider.name, time.perf_counter() - t0, ok=False)

        ordered = hb.order(["pixabay", "wikimedia", "pexels"])
    """

    def __init__(
        self,
        alpha: float = _DEFAULT_ALPHA,
        down_threshold: float = _DOWN_THRESHOLD,
    ):
        self._alpha = alpha
        self._down_threshold = down_threshold
        self._stats: Dict[str, _ProviderStats] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface (MS §17.2 contract)
    # ------------------------------------------------------------------

    def report(self, provider: str, latency_s: float, ok: bool) -> None:
        """Update EMA stats for a provider after a call completes.

        Args:
            provider:  Provider name string (e.g. "pixabay", "wikimedia").
            latency_s: Wall-clock seconds the call took.
            ok:        True if the call returned usable results; False on error/timeout.
        """
        with self._lock:
            stats = self._stats.setdefault(provider, _ProviderStats())
            a = self._alpha
            stats.latency_ema = a * latency_s + (1 - a) * stats.latency_ema
            stats.success_ema = a * float(ok) + (1 - a) * stats.success_ema
            stats.call_count += 1
            stats.last_call_ts = time.time()

        logger.debug(
            f"HealthBoard.report({provider}): "
            f"latency={latency_s:.3f}s ok={ok} → "
            f"ema_lat={stats.latency_ema:.3f} ema_ok={stats.success_ema:.3f}"
        )

    def order(self, providers: List[str]) -> List[str]:
        """Return providers sorted by health score (best first).

        Providers not yet seen receive neutral default stats.
        Providers whose success_ema < down_threshold are pushed to the end.
        """
        with self._lock:
            stats_snapshot = {p: self._stats.get(p, _ProviderStats()) for p in providers}

        healthy = [p for p in providers if not stats_snapshot[p].is_down]
        down = [p for p in providers if stats_snapshot[p].is_down]

        healthy.sort(key=lambda p: stats_snapshot[p].score, reverse=True)

        if down:
            logger.debug(
                f"HealthBoard.order: providers marked down: {down}"
            )

        result = healthy + down
        logger.debug(f"HealthBoard.order({providers}) → {result}")
        return result

    # ------------------------------------------------------------------
    # Diagnostics / introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Dict]:
        """Return a serialisable snapshot of all provider stats."""
        with self._lock:
            return {
                p: {
                    "latency_ema": round(s.latency_ema, 4),
                    "success_ema": round(s.success_ema, 4),
                    "score": round(s.score, 6),
                    "call_count": s.call_count,
                    "is_down": s.is_down,
                }
                for p, s in self._stats.items()
            }

    def reset(self, provider: Optional[str] = None) -> None:
        """Reset stats for one provider, or all if provider is None."""
        with self._lock:
            if provider is None:
                self._stats.clear()
            else:
                self._stats.pop(provider, None)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_global_health_board: Optional[HealthBoard] = None


def get_health_board() -> HealthBoard:
    """Lazy singleton — one HealthBoard per process lifetime."""
    global _global_health_board
    if _global_health_board is None:
        _global_health_board = HealthBoard()
    return _global_health_board
