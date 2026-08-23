"""AnkiAI Stroke-Based Icon System — Cinematic Dark Design.

Replaces emoji text with crisp, animatable QPainter stroke icons that match
the cinematic-dark UI (deep midnight surfaces, cyan accent #00b4d8).

Icons
-----
All paths are authored on a **24 × 24** grid with **1.8 px** stroke,
round cap / round join.  Each icon is a ``QPainterPath`` rendered inside
an ``AnimatableIcon`` widget that exposes three ``pyqtProperty`` slots:

    progress  0.0 → 1.0   draw-on animation  (stroke reveals over 450 ms)
    scale     1.0 → 1.3 → 1.0   pop / press  (350 ms OutBack easing)
    angle     0 → 360          rotation        (spinner / refresh)

Usage::

    from .ui_icons import CheckIcon, SpinnerIcon, svg_of, IconName

    icon = CheckIcon(size=20)           # green checkmark widget
    icon.draw_on()                      # animate stroke reveal

    spinner = SpinnerIcon(size=16)      # auto-rotating spinner

    html_snippet = svg_of("spark")      # SVG string for webview

Compatible with Python 3.9 – 3.13, Qt 5 / Qt 6 (via ``aqt.qt`` shim).
"""

from __future__ import annotations

import enum
import math
import logging
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Qt imports — prefer aqt.qt (Anki shim), fall back to PyQt6 / PyQt5
# ---------------------------------------------------------------------------
try:
    from aqt.qt import (  # type: ignore[import-untyped]
        QWidget,
        QPainter,
        QPainterPath,
        QPen,
        QColor,
        QPropertyAnimation,
        QEasingCurve,
        QRectF,
        QPointF,
        Qt,
        QSize,
    )
    try:
        from aqt.qt import pyqtProperty  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        from PyQt6.QtCore import pyqtProperty  # type: ignore[import-untyped]
except ImportError:
    try:
        from PyQt6.QtWidgets import QWidget  # type: ignore[import-untyped]
        from PyQt6.QtGui import (
            QPainter,
            QPainterPath,
            QPen,
            QColor,
        )
        from PyQt6.QtCore import (
            QPropertyAnimation,
            QEasingCurve,
            QRectF,
            QPointF,
            Qt,
            QSize,
            pyqtProperty,
        )
    except ImportError:
        from PyQt5.QtWidgets import QWidget  # type: ignore[import-untyped]
        from PyQt5.QtGui import (
            QPainter,
            QPainterPath,
            QPen,
            QColor,
        )
        from PyQt5.QtCore import (
            QPropertyAnimation,
            QEasingCurve,
            QRectF,
            QPointF,
            Qt,
            QSize,
            pyqtProperty,
        )

logger = logging.getLogger(__name__)


# ============================================================================
# 1. DESIGN-SYSTEM COLOUR CONSTANTS
# ============================================================================

ACCENT: str = "#00b4d8"   # Cyan — primary accent
BRIGHT: str = "#00e5ff"   # Bright cyan — highlights
OK: str = "#3fb950"       # Green — success / check
WARN: str = "#d29922"     # Amber — warning
DANGER: str = "#f85149"   # Red — error / cross
TEXT_LOW: str = "#8b949e" # Muted — low-emphasis text / icons


# ============================================================================
# 2. ICON NAME ENUM (Qt6-scoped, plain Enum)
# ============================================================================

class IconName(enum.Enum):
    """Canonical names for every icon in the system."""
    CHECK = "check"
    CROSS = "cross"
    WARNING = "warning"
    SPARK = "spark"
    THUMB_UP = "thumb-up"
    THUMB_DOWN = "thumb-down"
    SPINNER = "spinner"
    SLASH = "slash"
    REFRESH = "refresh"
    DOT = "dot"


# ============================================================================
# 3. SVG PATH DATA  (24 × 24 grid, stroke 1.8 px, round cap/join)
# ============================================================================
# Each value is a list of *sub-path* strings.  Each sub-path string uses an
# SVG-like mini-language that we translate to QPainterPath commands:
#
#   M x y         → moveTo
#   L x y         → lineTo
#   A rx ry rot    → arcTo  (large-arc / sweep encoded in params below)
#     large sweep
#     x y
#   Z             → closeSubpath
#
# For more complex shapes we store pre-built builder callables (see _build_*).
# This keeps the data declarative while still allowing arcs and cubics.

def _build_check(p: QPainterPath) -> None:
    """✓  single-stroke checkmark."""
    p.moveTo(4.5, 12.5)
    p.lineTo(9.5, 17.5)
    p.lineTo(19.5, 6.5)


def _build_cross(p: QPainterPath) -> None:
    """✗  two crossing strokes."""
    p.moveTo(5.5, 5.5)
    p.lineTo(18.5, 18.5)
    p.moveTo(18.5, 5.5)
    p.lineTo(5.5, 18.5)


def _build_warning(p: QPainterPath) -> None:
    """⚠  triangle outline + exclamation bar + dot."""
    # Triangle
    p.moveTo(12.0, 2.5)
    p.lineTo(22.0, 20.0)
    p.lineTo(2.0, 20.0)
    p.closeSubpath()
    # Exclamation bar
    p.moveTo(12.0, 9.0)
    p.lineTo(12.0, 14.5)
    # Exclamation dot (tiny vertical stub rendered with round cap)
    p.moveTo(12.0, 17.0)
    p.lineTo(12.0, 17.01)


def _build_spark(p: QPainterPath) -> None:
    """✦  4-pointed star (brand / empty-state)."""
    # Outer points: top, right, bottom, left  at radius ~10
    # Inner points at radius ~3.5
    cx, cy = 12.0, 12.0
    ro, ri = 10.0, 3.5
    angles_out = [270, 0, 90, 180]      # N E S W
    angles_in = [315, 45, 135, 225]     # NE SE SW NW

    pts = []
    for i in range(4):
        a_out = math.radians(angles_out[i])
        a_in = math.radians(angles_in[i])
        pts.append((cx + ro * math.cos(a_out), cy + ro * math.sin(a_out)))
        pts.append((cx + ri * math.cos(a_in), cy + ri * math.sin(a_in)))

    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.closeSubpath()


def _build_thumb_up(p: QPainterPath) -> None:
    """👍  simplified thumbs-up outline."""
    # Thumb (upper portion)
    p.moveTo(7.0, 11.0)
    p.lineTo(7.0, 21.0)
    p.lineTo(10.5, 21.0)
    p.lineTo(10.5, 11.0)

    # Hand outline — top curve and fingers
    p.moveTo(10.5, 11.0)
    p.lineTo(10.5, 7.0)
    p.cubicTo(10.5, 4.0, 12.0, 2.5, 13.0, 2.5)
    p.cubicTo(14.0, 2.5, 14.5, 3.5, 14.5, 5.0)
    p.lineTo(14.5, 9.0)
    p.lineTo(20.0, 9.0)
    p.cubicTo(21.5, 9.0, 22.0, 10.0, 21.5, 11.5)
    p.lineTo(19.5, 19.5)
    p.cubicTo(19.2, 20.5, 18.5, 21.0, 17.5, 21.0)
    p.lineTo(10.5, 21.0)


def _build_spinner(p: QPainterPath) -> None:
    """◔  270° arc (3/4 circle) — loading indicator."""
    rect = QRectF(3.0, 3.0, 18.0, 18.0)
    p.arcMoveTo(rect, 90)          # start at 12-o'clock
    p.arcTo(rect, 90, -270)        # sweep 270° clockwise


def _build_slash(p: QPainterPath) -> None:
    """⊘  circle with diagonal slash — skipped state."""
    rect = QRectF(3.0, 3.0, 18.0, 18.0)
    p.moveTo(12.0, 3.0)
    p.arcTo(rect, 90, 360)        # full circle
    # Diagonal
    p.moveTo(6.3, 6.3)
    p.lineTo(17.7, 17.7)


def _build_refresh(p: QPainterPath) -> None:
    """⟳  circular arrow — retry."""
    rect = QRectF(3.0, 3.0, 18.0, 18.0)
    p.arcMoveTo(rect, 60)
    p.arcTo(rect, 60, 300)        # 300° arc
    # Arrow head at end of arc (approx 60° position)
    ax = 12.0 + 9.0 * math.cos(math.radians(60))
    ay = 12.0 - 9.0 * math.sin(math.radians(60))
    p.moveTo(ax - 2.5, ay - 2.0)
    p.lineTo(ax, ay)
    p.lineTo(ax + 1.5, ay - 3.0)


def _build_dot(p: QPainterPath) -> None:
    """●  small filled circle — status dot."""
    rect = QRectF(8.0, 8.0, 8.0, 8.0)
    p.moveTo(16.0, 12.0)
    p.arcTo(rect, 0, 360)


# Registry: name → builder callable
_ICON_BUILDERS: Dict[str, callable] = {
    "check":      _build_check,
    "cross":      _build_cross,
    "warning":    _build_warning,
    "spark":      _build_spark,
    "thumb-up":   _build_thumb_up,
    "thumb-down": _build_thumb_up,   # same path, flipped vertically at paint time
    "spinner":    _build_spinner,
    "slash":      _build_slash,
    "refresh":    _build_refresh,
    "dot":        _build_dot,
}


# ============================================================================
# 4. ANIMATABLE ICON — base QWidget with progress / scale / angle properties
# ============================================================================

class AnimatableIcon(QWidget):
    """Stroke-based icon widget with three animate-able properties.

    Parameters
    ----------
    size : int
        Pixel size of the square icon (default 24).
    color : str
        Hex colour for the stroke pen (default ACCENT).
    stroke : float
        Stroke width in logical pixels (default 1.8).
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(
        self,
        size: int = 24,
        color: str = ACCENT,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._stroke = stroke
        self._flip_v: bool = False

        # Animate-able state
        self._progress: float = 1.0   # 1.0 = fully drawn
        self._scale: float = 1.0
        self._angle: float = 0.0

        # Active animations (managed by helper methods)
        self._anim_progress: Optional[QPropertyAnimation] = None
        self._anim_scale: Optional[QPropertyAnimation] = None
        self._anim_angle: Optional[QPropertyAnimation] = None

        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    # ── pyqtProperty: progress ──────────────────────────────────────────────

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    progress = pyqtProperty(float, fget=_get_progress, fset=_set_progress)

    # ── pyqtProperty: scale ─────────────────────────────────────────────────

    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, value: float) -> None:
        self._scale = float(value)
        self.update()

    scale = pyqtProperty(float, fget=_get_scale, fset=_set_scale)

    # ── pyqtProperty: angle ─────────────────────────────────────────────────

    def _get_angle(self) -> float:
        return self._angle

    def _set_angle(self, value: float) -> None:
        self._angle = float(value) % 360.0
        self.update()

    angle = pyqtProperty(float, fget=_get_angle, fset=_set_angle)

    # ── Public helpers ──────────────────────────────────────────────────────

    def set_color(self, color: str) -> None:
        """Change the stroke colour and repaint."""
        self._color = QColor(color)
        self.update()

    def set_flip_v(self, flip: bool) -> None:
        """Mirror the icon vertically (used by ThumbDownIcon)."""
        self._flip_v = flip
        self.update()

    def draw_on(self, duration: int = 450) -> None:
        """Animate the stroke drawing in from 0 → 1 over *duration* ms."""
        if self._anim_progress is not None:
            self._anim_progress.stop()
            self._anim_progress.deleteLater()

        self._progress = 0.0
        self._anim_progress = QPropertyAnimation(self, b"progress")
        self._anim_progress.setDuration(duration)
        self._anim_progress.setStartValue(0.0)
        self._anim_progress.setEndValue(1.0)
        self._anim_progress.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_progress.start()

    def pop(self, duration: int = 350) -> None:
        """Pop / press animation: scale 1.0 → 1.3 → 1.0 with OutBack."""
        if self._anim_scale is not None:
            self._anim_scale.stop()
            self._anim_scale.deleteLater()

        self._anim_scale = QPropertyAnimation(self, b"scale")
        self._anim_scale.setDuration(duration)
        self._anim_scale.setStartValue(1.0)
        self._anim_scale.setKeyValueAt(0.4, 1.3)
        self._anim_scale.setEndValue(1.0)
        self._anim_scale.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim_scale.start()

    # ── Geometry helpers ────────────────────────────────────────────────────

    def sizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    def minimumSizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    # ── Path building (override in subclasses) ──────────────────────────────

    def _build_path(self, path: QPainterPath) -> None:
        """Populate *path* with this icon's geometry.

        Subclasses **must** override this method.
        """
        raise NotImplementedError

    # ── Paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802  (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        side = self._size
        painter.translate(side / 2.0, side / 2.0)

        # Rotation
        if self._angle != 0.0:
            painter.rotate(self._angle)

        # Scale
        if self._scale != 1.0:
            painter.scale(self._scale, self._scale)

        # Vertical flip (thumb-down)
        if self._flip_v:
            painter.scale(1.0, -1.0)

        painter.translate(-side / 2.0, -side / 2.0)

        # Build the full path
        full_path = QPainterPath()
        self._build_path(full_path)

        # Clip to progress fraction
        draw_path = self._partial_path(full_path, self._progress)

        # Pen setup
        pen = QPen(self._color, self._stroke)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawPath(draw_path)
        painter.end()

    # ── Partial-path helper ─────────────────────────────────────────────────

    @staticmethod
    def _partial_path(source: QPainterPath, fraction: float) -> QPainterPath:
        """Return a QPainterPath representing *fraction* (0–1) of *source*.

        Uses ``percentAtLength`` to walk the source path and build a
        truncated copy.  When *fraction* ≥ 1 the full path is returned.
        """
        if fraction >= 1.0:
            return QPainterPath(source)

        total = source.length()
        if total <= 0.0 or fraction <= 0.0:
            return QPainterPath()

        target_len = total * fraction
        result = QPainterPath()
        started = False

        # Walk the path in small steps
        step = max(0.5, total / 500.0)  # ~500 segments max
        t = 0.0
        while t <= target_len:
            pct = t / total if total > 0 else 0.0
            pt = source.pointAtPercent(pct)
            if not started:
                result.moveTo(pt)
                started = True
            else:
                result.lineTo(pt)
            t += step

        # Final point at exact target
        pct_final = target_len / total if total > 0 else 0.0
        pt_final = source.pointAtPercent(pct_final)
        if not started:
            result.moveTo(pt_final)
        else:
            result.lineTo(pt_final)

        return result


# ============================================================================
# 5. CONCRETE ICON CLASSES
# ============================================================================

class CheckIcon(AnimatableIcon):
    """✓  Success / confirmed state (green by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = OK,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_check(path)


class CrossIcon(AnimatableIcon):
    """✗  Error / rejected state (red by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = DANGER,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_cross(path)


class WarningIcon(AnimatableIcon):
    """⚠  Warning / caution state (amber by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = WARN,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_warning(path)


class SparkIcon(AnimatableIcon):
    """✦  Brand / empty-state sparkle (cyan by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = ACCENT,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_spark(path)


class ThumbUpIcon(AnimatableIcon):
    """👍  Thumbs-up / like (muted by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = TEXT_LOW,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_thumb_up(path)


class ThumbDownIcon(AnimatableIcon):
    """👎  Thumbs-down / dislike (muted, vertically flipped)."""

    def __init__(
        self,
        size: int = 24,
        color: str = TEXT_LOW,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)
        self._flip_v = True

    def _build_path(self, path: QPainterPath) -> None:
        _build_thumb_up(path)  # same geometry, flipped via _flip_v


class SpinnerIcon(AnimatableIcon):
    """◔  270° arc — auto-rotating loading spinner (cyan by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = ACCENT,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)
        self._start_spin()

    def _build_path(self, path: QPainterPath) -> None:
        _build_spinner(path)

    def _start_spin(self) -> None:
        """Begin infinite rotation animation."""
        if self._anim_angle is not None:
            self._anim_angle.stop()
            self._anim_angle.deleteLater()

        self._anim_angle = QPropertyAnimation(self, b"angle")
        self._anim_angle.setDuration(1000)
        self._anim_angle.setStartValue(0.0)
        self._anim_angle.setEndValue(360.0)
        self._anim_angle.setLoopCount(-1)  # infinite
        self._anim_angle.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim_angle.start()

    def stop_spin(self) -> None:
        """Stop the rotation animation."""
        if self._anim_angle is not None:
            self._anim_angle.stop()
            self._anim_angle.deleteLater()
            self._anim_angle = None


class SlashIcon(AnimatableIcon):
    """⊘  Circle with diagonal slash — skipped state (muted by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = TEXT_LOW,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_slash(path)


class RefreshIcon(AnimatableIcon):
    """⟳  Circular arrow — retry action (cyan by default)."""

    def __init__(
        self,
        size: int = 24,
        color: str = ACCENT,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_refresh(path)


class DotIcon(AnimatableIcon):
    """●  Small filled circle — status dot (cyan by default).

    The dot is rendered as a stroked circle whose stroke width equals
    the radius, giving a solid-fill appearance at any size.
    """

    def __init__(
        self,
        size: int = 24,
        color: str = ACCENT,
        stroke: float = 1.8,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(size, color, stroke, parent)

    def _build_path(self, path: QPainterPath) -> None:
        _build_dot(path)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Override: render as a filled circle instead of stroked."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        side = self._size
        painter.translate(side / 2.0, side / 2.0)
        if self._angle != 0.0:
            painter.rotate(self._angle)
        if self._scale != 1.0:
            painter.scale(self._scale, self._scale)
        painter.translate(-side / 2.0, -side / 2.0)

        # Filled circle — 4 px radius centred in the widget
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(QPointF(side / 2.0, side / 2.0), 4.0, 4.0)
        painter.end()


# ============================================================================
# 6. ICON CLASS REGISTRY (for factory usage)
# ============================================================================

ICON_CLASSES: Dict[str, type] = {
    "check":      CheckIcon,
    "cross":      CrossIcon,
    "warning":    WarningIcon,
    "spark":      SparkIcon,
    "thumb-up":   ThumbUpIcon,
    "thumb-down": ThumbDownIcon,
    "spinner":    SpinnerIcon,
    "slash":      SlashIcon,
    "refresh":    RefreshIcon,
    "dot":        DotIcon,
}


def icon_factory(
    name: str,
    size: int = 24,
    color: Optional[str] = None,
    stroke: float = 1.8,
    parent: Optional[QWidget] = None,
) -> AnimatableIcon:
    """Create an icon widget by name.

    Parameters
    ----------
    name : str
        One of the ``IconName`` values (e.g. ``"check"``, ``"spinner"``).
    size : int
        Pixel size of the icon (default 24).
    color : str | None
        Override colour; ``None`` uses the icon class default.
    stroke : float
        Stroke width (default 1.8).
    parent : QWidget | None
        Optional parent.

    Returns
    -------
    AnimatableIcon
        A ready-to-show icon widget.

    Raises
    ------
    KeyError
        If *name* is not a recognised icon.
    """
    cls = ICON_CLASSES[name]
    kwargs: dict = dict(size=size, stroke=stroke, parent=parent)
    if color is not None:
        kwargs["color"] = color
    return cls(**kwargs)


# ============================================================================
# 7. SVG STRING GENERATOR (for HTML / webview contexts)
# ============================================================================

def _builder_to_svg_path_d(name: str) -> str:
    """Convert a builder's QPainterPath to an SVG ``d`` attribute string.

    We replay the builder into a QPainterPath, then walk its elements
    to produce SVG path commands.
    """
    p = QPainterPath()
    builder = _ICON_BUILDERS.get(name)
    if builder is None:
        return ""
    builder(p)

    parts: list[str] = []
    i = 0
    count = p.elementCount()
    while i < count:
        el = p.elementAt(i)
        # QPainterPath.ElementType: 0=MoveTo, 1=LineTo, 2=CurveTo, 3=CurveToData
        etype = el.type
        if etype == 0:  # MoveToElement
            parts.append(f"M{el.x:.2f},{el.y:.2f}")
        elif etype == 1:  # LineToElement
            parts.append(f"L{el.x:.2f},{el.y:.2f}")
        elif etype == 2:  # CurveToElement (start of cubic triplet)
            if i + 2 < count:
                c1 = p.elementAt(i)
                c2 = p.elementAt(i + 1)
                c3 = p.elementAt(i + 2)
                parts.append(
                    f"C{c1.x:.2f},{c1.y:.2f} "
                    f"{c2.x:.2f},{c2.y:.2f} "
                    f"{c3.x:.2f},{c3.y:.2f}"
                )
                i += 2  # skip the two data elements
        i += 1

    # Close if the path was closed
    # QPainterPath doesn't expose a simple "is closed" flag per subpath,
    # but our builders that call closeSubpath will have the last lineTo
    # back to the moveTo point.  We emit Z when appropriate.
    # For simplicity, check if first and last points match.
    if count >= 2:
        first = p.elementAt(0)
        last = p.elementAt(count - 1)
        if (abs(first.x - last.x) < 0.01 and abs(first.y - last.y) < 0.01
                and name in ("warning", "spark", "slash")):
            parts.append("Z")

    return " ".join(parts)


def svg_of(
    name: str,
    size: int = 24,
    color: str = ACCENT,
    stroke: float = 1.8,
) -> str:
    """Return an SVG string for the named icon.

    Useful for embedding in QWebEngineView, QWebEnginePage, or Anki's
    ``reviewer`` HTML templates.

    Parameters
    ----------
    name : str
        Icon name (see ``IconName`` enum).
    size : int
        ViewBox size in px (default 24).
    color : str
        Stroke colour as hex string.
    stroke : float
        Stroke width.

    Returns
    -------
    str
        Complete ``<svg>`` element as a string.

    Raises
    ------
    KeyError
        If *name* is not a recognised icon.
    """
    if name not in _ICON_BUILDERS:
        raise KeyError(f"Unknown icon name: {name!r}")

    # Special case: dot is a filled circle — use <circle> element
    if name == "dot":
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{size}" height="{size}" viewBox="0 0 24 24">'
            f'<circle cx="12" cy="12" r="4" fill="{color}" />'
            f'</svg>'
        )

    d = _builder_to_svg_path_d(name)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{d}" />'
        f'</svg>'
    )
