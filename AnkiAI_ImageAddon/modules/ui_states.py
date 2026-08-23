# -*- coding: utf-8 -*-
"""AnkiAI — Empty / Error / Skeleton / Loading state system.

Implements File 1 §8 (Cinematic Dark · Electric Cyan):
  - Skeleton shimmer uses CYAN rgba(0,229,255,0.10) — matches the chosen style.
  - Every content region must be one of 4 states: loading / empty / error / content.
  - ``StateStack`` switches between states with a soft fade.

Qt6 scoped enums are used (errata E3); alpha colours use rgba() (errata E1).
"""
from __future__ import annotations

from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QPainter,
    QColor,
    QSizePolicy,
    QPropertyAnimation,
    QEasingCurve,
    QGraphicsOpacityEffect,
    Qt,
)
try:
    from aqt.qt import pyqtProperty, QRectF, QPainterPath, QBrush, QLinearGradient
except ImportError:  # pragma: no cover — fallback for some Anki builds
    from PyQt6.QtCore import pyqtProperty, QRectF
    from PyQt6.QtGui import QPainterPath, QBrush, QLinearGradient

# ── Token mirror (File 1 §2.1) ──────────────────────────────────────────────
RAISED = "#161c26"
OVERLAY = "#1c2430"
BORDER = "#232c3b"
ACCENT = "#00b4d8"
ACCENT_BRIGHT = "#00e5ff"
TEXT_HI = "#e6edf3"
TEXT_MID = "#c9d1d9"
TEXT_LOW = "#8b949e"
OK = "#3fb950"
WARN = "#d29922"
DANGER = "#f85149"

_ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter


def _fade_in(w: QWidget, dur: int = 220) -> None:
    """Soft fade used when switching states in :class:`StateStack`."""
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    eff.setOpacity(0.0)
    a = QPropertyAnimation(eff, b"opacity", w)
    a.setDuration(dur)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    a.finished.connect(lambda: w.setGraphicsEffect(None))
    w._state_fade = a  # prevent GC
    a.start()


# ─────────────────────────────────────────────────────────────────────────────
# SKELETON (cyan shimmer)
# ─────────────────────────────────────────────────────────────────────────────

class SkeletonBar(QWidget):
    """Rounded placeholder bar with a looping cyan shimmer sweep."""

    def __init__(self, height: int = 12, radius: int = 6, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setMinimumWidth(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._r = radius
        self._p = 0.0
        self._anim = None

    def _gp(self) -> float:
        return self._p

    def _sp(self, v: float) -> None:
        self._p = v
        self.update()

    progress = pyqtProperty(float, fget=_gp, fset=_sp)

    def start(self) -> None:
        if self._anim:
            return
        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(1200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim.start()

    def stop(self) -> None:
        if self._anim:
            self._anim.stop()
            self._anim = None

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), self._r, self._r)
        p.fillPath(path, QColor(RAISED))
        p.setClipPath(path)
        bw = max(40.0, w * 0.35)
        cx = self._p * (w + bw) - bw
        g = QLinearGradient(cx, 0, cx + bw, 0)
        g.setColorAt(0.0, QColor("rgba(0,229,255,0)"))
        g.setColorAt(0.5, QColor("rgba(0,229,255,0.10)"))  # shimmer CYAN
        g.setColorAt(1.0, QColor("rgba(0,229,255,0)"))
        p.fillRect(QRectF(cx, 0, bw, h), QBrush(g))
        p.setClipping(False)


class SkeletonPreviewCard(QWidget):
    """Skeleton that mirrors the :class:`ImagePreviewCard` layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(
            f"background:{OVERLAY};border:1px solid {BORDER};border-radius:14px"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)
        self._bars = [
            SkeletonBar(120, 8),
            SkeletonBar(14, 6),
            SkeletonBar(10, 5),
            SkeletonBar(24, 12),
        ]
        for b in self._bars:
            lay.addWidget(b)
        lay.addStretch()

    def start(self) -> None:
        for b in self._bars:
            b.start()

    def stop(self) -> None:
        for b in self._bars:
            b.stop()


# ─────────────────────────────────────────────────────────────────────────────
# LOADING
# ─────────────────────────────────────────────────────────────────────────────

class LoadingRow(QWidget):
    """Spinner + label — the default "working" indicator."""

    def __init__(self, text: str = "Đang tìm ảnh…", parent=None):
        super().__init__(parent)
        from .ui_icons import SpinnerIcon

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.spin = SpinnerIcon(20)
        self.spin.start()
        self.lbl = QLabel(text)
        self.lbl.setStyleSheet(f"color:{TEXT_MID};font-size:13px;background:transparent")
        lay.addWidget(self.spin)
        lay.addWidget(self.lbl)
        lay.addStretch()

    def set_text(self, t: str) -> None:
        self.lbl.setText(t)

    def start(self) -> None:
        if hasattr(self.spin, "start"):
            self.spin.start()

    def stop(self) -> None:
        if hasattr(self.spin, "stop"):
            self.spin.stop()


# ─────────────────────────────────────────────────────────────────────────────
# EMPTY / ERROR
# ─────────────────────────────────────────────────────────────────────────────

class StateMessage(QWidget):
    """Centered glyph + title + description + optional action buttons."""

    def __init__(self, glyph: str, glyph_color: str, title: str,
                 desc: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(10)
        lay.setAlignment(_ALIGN_CENTER)

        g = QLabel(glyph)
        g.setAlignment(_ALIGN_CENTER)
        g.setStyleSheet(f"font-size:38px;color:{glyph_color};background:transparent")
        lay.addWidget(g)

        t = QLabel(title)
        t.setAlignment(_ALIGN_CENTER)
        t.setWordWrap(True)
        t.setStyleSheet(f"font-size:15px;font-weight:700;color:{TEXT_HI};background:transparent")
        lay.addWidget(t)

        if desc:
            d = QLabel(desc)
            d.setAlignment(_ALIGN_CENTER)
            d.setWordWrap(True)
            d.setMaximumWidth(360)
            d.setStyleSheet(f"font-size:12px;color:{TEXT_LOW};background:transparent")
            lay.addWidget(d)

        self._btns = QHBoxLayout()
        self._btns.setAlignment(_ALIGN_CENTER)
        self._btns.setSpacing(10)
        lay.addLayout(self._btns)

    def add_button(self, text: str, obj_name: str, cb) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName(obj_name)
        b.clicked.connect(cb)
        self._btns.addWidget(b)
        return b


def EmptyState(title: str, desc: str = "", glyph: str = "✦", parent=None) -> StateMessage:
    """Empty-state block (accent glyph)."""
    return StateMessage(glyph, ACCENT, title, desc, parent)


def ErrorState(title: str, desc: str = "", hard: bool = False, parent=None) -> StateMessage:
    """Error block. ``hard=True`` → danger ✗ (retryable); else warn ⚠."""
    return StateMessage("✗" if hard else "⚠", DANGER if hard else WARN,
                        title, desc, parent)


# ─────────────────────────────────────────────────────────────────────────────
# STATE STACK
# ─────────────────────────────────────────────────────────────────────────────

class StateStack(QWidget):
    """Switch between loading / empty / error / content pages by fade.

    Usage::

        stack = StateStack()
        stack.add("content", content_widget)
        stack.add("loading", LoadingRow())
        stack.show("loading")
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack = QStackedWidget(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._stack)
        self._pages = {}

    def add(self, name: str, widget: QWidget) -> QWidget:
        self._pages[name] = widget
        self._stack.addWidget(widget)
        return widget

    def show(self, name: str, fade: bool = True) -> None:
        w = self._pages.get(name)
        if not w:
            return
        current = self._stack.currentWidget()
        if current is not None:
            for child in current.findChildren(QWidget):
                if hasattr(child, "stop"):
                    child.stop()
        self._stack.setCurrentWidget(w)
        if hasattr(w, "start"):
            w.start()
        if fade:
            _fade_in(w)
