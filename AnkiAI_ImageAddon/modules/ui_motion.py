"""Cinematic-dark UI motion system for AnkiAI ImageAddon.

Provides entrance animations, state transitions, and micro-interactions.
All timing constants are centralized in the ``Motion`` class. Every public
function honours the ``ui_reduce_motion`` config flag so users who prefer
less motion get instant state changes instead.

Technical notes
---------------
* All Qt imports come from ``aqt.qt`` (Anki's Qt wrapper).
* Animation objects are stored on their target widgets (``widget._fade_anim``,
  ``widget._fade_effect``, etc.) to prevent garbage collection while running.
* Python 3.9 compatible — uses ``from __future__ import annotations``.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from aqt.qt import (
    QObject,
    QPropertyAnimation,
    QEasingCurve,
    QGraphicsOpacityEffect,
    QLabel,
    QProgressBar,
    QTimeLine,
    QWidget,
    pyqtProperty,  # type: ignore[attr-defined]
    pyqtSlot,  # type: ignore[attr-defined]
)


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def _get_config() -> dict:
    """Lazy-load addon config for motion preference check."""
    try:
        from .config import ConfigManager  # type: ignore[import-untyped]
        return ConfigManager.get_config()
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Timing constants
# ---------------------------------------------------------------------------

class Motion:
    """Centralized animation timing constants (milliseconds).

    Timings follow the Cinematic Dark design system (File 1 §7.1):
    dur_fast=120, dur_base=200, dur_enter=450, dur_count=900, stagger=80.
    """

    FAST = 120      # Quick feedback (hover, press)
    BASE = 200      # Standard transitions
    ENTER = 450     # Entrance animations (rich cinematic feel)
    COUNT = 900     # Count-up number animations
    STAGGER = 80    # Delay between staggered items

    @staticmethod
    def reduced(config: dict | None = None) -> bool:
        """Return ``True`` if the user has disabled motion.

        Reads the ``ui_reduce_motion`` key from the addon config dict.
        An explicit *config* parameter takes precedence; when ``None`` the
        config is loaded lazily via :func:`_get_config`.
        """
        if config is None:
            config = _get_config()
        return bool(config.get("ui_reduce_motion", False))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _CountUpDriver(QObject):
    """Drives a smooth integer count-up on a :class:`QLabel`.

    We animate a *float* property with :class:`QTimeLine` (frame-callback
    approach) so the label text updates every visual frame.  Using
    ``QTimeLine`` instead of ``QPropertyAnimation`` on a custom property
    avoids metaclass / sip issues on some Anki builds.
    """

    def __init__(
        self,
        label: QLabel,
        target: int,
        duration: int,
        prefix: str,
        suffix: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._target = target
        self._prefix = prefix
        self._suffix = suffix

        self._timeline = QTimeLine(duration, self)
        self._timeline.setFrameRange(0, duration)
        self._timeline.setCurveShape(QTimeLine.CurveShape.EaseOutCubic)
        self._timeline.frameChanged.connect(self._on_frame)  # type: ignore[attr-defined]

    # -- slot ---------------------------------------------------------------

    @pyqtSlot(int)
    def _on_frame(self, frame: int) -> None:
        duration = self._timeline.duration()
        if duration <= 0:
            progress = 1.0
        else:
            progress = frame / duration

        # Apply OutCubic easing manually (QTimeLine EaseOutCubic approximation)
        eased = 1.0 - (1.0 - progress) ** 3
        current = int(eased * self._target)
        self._label.setText(f"{self._prefix}{current:,}{self._suffix}")

    # -- public -------------------------------------------------------------

    def start(self) -> None:
        self._timeline.start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fade_in(
    widget: QWidget,
    duration: int = Motion.ENTER,
    delay: int = 0,
    config: dict | None = None,
) -> Optional[QPropertyAnimation]:
    """Animate *widget* opacity from 0 → 1.

    Only opacity is animated — **not** geometry / position (errata E2: layout
    managers fight geometry animations).

    The ``QGraphicsOpacityEffect`` and ``QPropertyAnimation`` are stored on
    the widget (``_fade_effect`` / ``_fade_anim``) to keep them alive for the
    duration of the animation.

    Returns the ``QPropertyAnimation`` instance, or ``None`` when reduced
    motion is active (the widget is simply shown immediately).
    """
    if Motion.reduced(config):
        widget.setGraphicsEffect(None)
        widget.show()
        return None

    # Ensure widget starts invisible
    widget.hide()

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    widget._fade_effect = effect  # type: ignore[attr-defined]

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setFinalValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    if delay > 0:
        # QPropertyAnimation has no built-in delay; defer via single-shot timer.
        from aqt.qt import QTimer

        def _start_fade() -> None:
            widget.show()
            anim.start()

        timer = QTimer(widget)
        timer.setSingleShot(True)
        timer.timeout.connect(_start_fade)  # type: ignore[attr-defined]
        widget._fade_timer = timer  # type: ignore[attr-defined]
        widget._fade_start = _start_fade  # type: ignore[attr-defined]
        timer.start(delay)
    else:
        widget.show()
        anim.start()

    # Keep reference alive
    widget._fade_anim = anim  # type: ignore[attr-defined]
    return anim


def stagger_in(
    widgets: Sequence[QWidget],
    duration: int = Motion.ENTER,
    delay_step: int = Motion.STAGGER,
    config: dict | None = None,
) -> List[Optional[QPropertyAnimation]]:
    """Fade in *widgets* one after another with increasing delays.

    Each widget *i* starts its fade after ``i * delay_step`` milliseconds.
    Under reduced motion every widget is shown immediately.

    Returns a list of animation objects (may contain ``None`` entries).
    """
    if Motion.reduced(config):
        for w in widgets:
            w.show()
        return [None] * len(widgets)

    anims: list[Optional[QPropertyAnimation]] = []
    for i, w in enumerate(widgets):
        anim = fade_in(w, duration=duration, delay=i * delay_step, config=config)
        anims.append(anim)
    return anims


def count_up(
    label: QLabel,
    target_value: int,
    duration: int = Motion.COUNT,
    prefix: str = "",
    suffix: str = "",
    config: dict | None = None,
) -> Optional[_CountUpDriver]:
    """Animate a number from 0 to *target_value* on *label*.

    The label text is updated every frame with a thousand-separated integer,
    optionally wrapped in *prefix* / *suffix* (e.g. ``"$"``, ``"%"``).

    Under reduced motion the final value is set immediately and ``None`` is
    returned.
    """
    final_text = f"{prefix}{target_value:,}{suffix}"

    if Motion.reduced(config):
        label.setText(final_text)
        return None

    driver = _CountUpDriver(label, target_value, duration, prefix, suffix)
    label.setText(f"{prefix}0{suffix}")
    driver.start()

    # Prevent GC
    label._count_driver = driver  # type: ignore[attr-defined]
    return driver


def animate_progress(
    progress_bar: QProgressBar,
    target_value: int,
    duration: int = Motion.BASE,
    config: dict | None = None,
) -> Optional[QPropertyAnimation]:
    """Smoothly animate *progress_bar* from its current value to *target_value*.

    Uses ``QPropertyAnimation`` on the ``"value"`` property with
    ``OutCubic`` easing.  Under reduced motion the bar jumps straight to the
    target.
    """
    if Motion.reduced(config):
        progress_bar.setValue(target_value)
        return None

    anim = QPropertyAnimation(progress_bar, b"value")
    anim.setDuration(duration)
    anim.setStartValue(progress_bar.value())
    anim.setFinalValue(target_value)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()

    # Prevent GC
    progress_bar._progress_anim = anim  # type: ignore[attr-defined]
    return anim


def slide_fade_in(
    widget: QWidget,
    duration: int = Motion.ENTER,
    direction: str = "up",
    config: dict | None = None,
) -> Optional[QPropertyAnimation]:
    """Combined fade + subtle translate for **non-layout-managed** widgets.

    The widget fades in (opacity 0 → 1) while shifting 8 px in the given
    *direction* (``"up"`` or ``"down"``).  Because translating a widget that
    lives inside a ``QLayout`` causes layout fights, this function is
    intended only for absolutely-positioned or overlay widgets.

    Under reduced motion the widget is simply shown immediately.

    Returns the opacity ``QPropertyAnimation``, or ``None``.
    """
    if Motion.reduced(config):
        widget.setGraphicsEffect(None)
        widget.show()
        return None

    offset = -8 if direction == "up" else 8

    # --- opacity ---
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    widget._slide_fade_effect = effect  # type: ignore[attr-defined]

    fade_anim = QPropertyAnimation(effect, b"opacity")
    fade_anim.setDuration(duration)
    fade_anim.setStartValue(0.0)
    fade_anim.setFinalValue(1.0)
    fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # --- geometry slide (only safe outside layouts) ---
    orig_pos = widget.pos()
    start_y = orig_pos.y() + offset
    widget.move(orig_pos.x(), start_y)
    widget.hide()

    geo_anim = QPropertyAnimation(widget, b"pos")
    geo_anim.setDuration(duration)
    geo_anim.setStartValue(widget.pos())
    geo_anim.setEndValue(orig_pos)
    geo_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    widget.show()
    fade_anim.start()
    geo_anim.start()

    # Prevent GC
    widget._slide_fade_anim = fade_anim  # type: ignore[attr-defined]
    widget._slide_geo_anim = geo_anim  # type: ignore[attr-defined]
    return fade_anim
