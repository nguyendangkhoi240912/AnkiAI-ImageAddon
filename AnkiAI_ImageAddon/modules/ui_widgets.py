"""Reusable Qt primitives for AnkiAI — Cinematic Dark · Electric Cyan.

Visual language:
  - Deep midnight foundation (#0a0e14) with 4-layer elevation
  - Electric Cyan (#00b4d8) single accent — NO violet
  - Gradient #0077ff → #00e5ff on primary CTA buttons
  - Strong white typography with cool muted secondaries
  - Thin 1px borders — structural but not dominant
  - Cyan tinted skeleton shimmer

Components:
    header_section      — Bold dialog header with accent rule
    settings_section    — Dark elevated card container
    field_row           — Label + hint + badge
    CredentialField     — Secure API key input with eye toggle
    credential_field    — Factory for CredentialField
    password_field      — Simple password QLineEdit
    status_badge        — Semantic inline status pill
    info_banner         — Horizontal info/warning strip
    stat_row_widget     — 3-counter progress summary
    section_spacer      — Thin vertical spacer
    divider             — Horizontal rule separator
    make_settings_card  — Backward-compat alias
    card_header         — Backward-compat card title label
    QuotaRing           — Circular SVG quota arc indicator
    StatCard            — Stat card with gradient number + label
    ImagePreviewCard    — Image result card with thumbnail
"""

from aqt.qt import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QSizePolicy,
    QPainter,
    QColor,
    QPen,
    QFont,
)
try:
    from aqt.qt import QRectF, Qt
except ImportError:
    from PyQt6.QtCore import QRectF, Qt
from typing import Tuple, Optional
from .ui_theme import get_tokens, is_dark_mode


# ─────────────────────────────────────────────────────────────────────────────
# HEADER SECTION
# ─────────────────────────────────────────────────────────────────────────────

def header_section(title: str, subtitle: str = "", icon: str = "") -> QWidget:
    """
    Dialog header with bold title, muted subtitle, and thin rule.

    Layout:
        [icon]  TITLE TEXT                     (heading — 18px bold)
                muted subtitle text            (11px text_muted)
        ────────────────────────────────────
    """
    tokens = get_tokens()
    wrap = QWidget()
    wrap.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 12)
    layout.setSpacing(0)

    # Title row
    title_row = QHBoxLayout()
    title_row.setSpacing(10)
    title_row.setContentsMargins(0, 0, 0, 0)

    if icon:
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size: 17px; color: {tokens['accent']}; "
            f"padding: 0; background: transparent;"
        )
        icon_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        title_row.addWidget(icon_lbl)

    title_lbl = QLabel(title)
    title_lbl.setProperty("heading", True)
    title_row.addWidget(title_lbl)
    title_row.addStretch()
    layout.addLayout(title_row)

    # Subtitle
    if subtitle:
        sub_lbl = QLabel(subtitle)
        sub_lbl.setProperty("subheading", True)
        sub_lbl.setWordWrap(True)
        sub_lbl.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(sub_lbl)

    layout.addSpacing(12)

    # Accent rule — thin blue line
    rule = QFrame()
    rule.setFixedHeight(1)
    rule.setStyleSheet(
        f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        f" stop:0 {tokens['accent_dim']}, stop:0.6 {tokens['border_light']}, stop:1 transparent);"
        f" border: none;"
    )
    layout.addWidget(rule)

    return wrap


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS SECTION / CARD
# ─────────────────────────────────────────────────────────────────────────────

def settings_section(
    title: str = "",
    subtitle: str = "",
    icon: str = "",
) -> Tuple[QFrame, QVBoxLayout]:
    """
    Dark-surface card container. Returns (QFrame, inner QVBoxLayout).

    With title: shows uppercase accent label + optional subtitle + rule.
    Without title: plain padded container.
    """
    tokens = get_tokens()
    frame = QFrame()
    frame.setObjectName("settingsSection")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)

    if title:
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        hdr.setContentsMargins(0, 0, 0, 0)

        if icon:
            ic = QLabel(icon)
            ic.setStyleSheet(
                f"font-size: 13px; color: {tokens['accent']}; background: transparent;"
            )
            ic.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            hdr.addWidget(ic)

        title_lbl = QLabel(title)
        title_lbl.setProperty("cardTitle", True)
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setProperty("hint", True)
            sub.setWordWrap(True)
            layout.addWidget(sub)

        # Thin separator under card header
        sep = QFrame()
        sep.setObjectName("headerRule")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

    return frame, layout


def make_settings_card() -> Tuple[QFrame, QVBoxLayout]:
    """Backward-compatible alias for settings_section()."""
    return settings_section()


def card_header(icon: str, title: str) -> QLabel:
    """Backward-compatible card title label."""
    lbl = QLabel(f"{icon}  {title}" if icon else title)
    lbl.setProperty("cardTitle", True)
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# FIELD ROW
# ─────────────────────────────────────────────────────────────────────────────

def field_row(label: str, hint: str = "", badge: str = "") -> QWidget:
    """
    Label + optional hint + optional badge row.

    badge: "priority" | "recommended" | "optional" | custom string
    """
    wrap = QWidget()
    wrap.setStyleSheet("background: transparent;")
    col = QVBoxLayout(wrap)
    col.setContentsMargins(0, 4, 0, 2)
    col.setSpacing(3)

    top = QHBoxLayout()
    top.setSpacing(8)
    top.setContentsMargins(0, 0, 0, 0)

    lbl = QLabel(label)
    lbl.setProperty("fieldLabel", True)
    top.addWidget(lbl)

    if badge == "priority":
        b = QLabel("Bắt buộc")
        b.setProperty("badge", "priority")
        top.addWidget(b)
    elif badge == "recommended":
        b = QLabel("Khuyến nghị")
        b.setProperty("badge", "recommended")
        top.addWidget(b)
    elif badge == "optional":
        b = QLabel("Tùy chọn")
        b.setProperty("badge", "optional")
        top.addWidget(b)
    elif badge:
        b = QLabel(badge)
        b.setProperty("badge", "optional")
        top.addWidget(b)

    top.addStretch()
    col.addLayout(top)

    if hint:
        h = QLabel(hint)
        h.setProperty("hint", True)
        h.setWordWrap(True)
        col.addWidget(h)

    return wrap


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIAL FIELD
# ─────────────────────────────────────────────────────────────────────────────

def password_field(placeholder: str = "") -> QLineEdit:
    """Simple password QLineEdit (backward compat)."""
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    if placeholder:
        field.setPlaceholderText(placeholder)
    return field


class CredentialField(QWidget):
    """
    Secure API key input with show/hide toggle.

    Masked by default. Eye button reveals the value.
    Public API: .text(), .setText(), .setPlaceholderText(), .setEnabled()
    """

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.is_revealed = False
        self.setStyleSheet("background: transparent;")

        tokens = get_tokens()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        if placeholder:
            self.input.setPlaceholderText(placeholder)
        layout.addWidget(self.input, stretch=1)

        self.toggle_btn = QPushButton("●●●")
        self.toggle_btn.setFixedWidth(42)
        self.toggle_btn.setFixedHeight(38)
        self.toggle_btn.setToolTip("Hiện / Ẩn key")
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens['bg_surface']};
                color: {tokens['text_low']};
                border: 1px solid {tokens['border']};
                border-radius: 8px;
                font-size: 8px;
                letter-spacing: 2px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {tokens['bg_raised']};
                border-color: {tokens['border_accent']};
                color: {tokens['accent']};
            }}
        """)
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.toggle_btn)

    def _toggle_visibility(self):
        tokens = get_tokens()
        self.is_revealed = not self.is_revealed
        if self.is_revealed:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("◉")
            self.toggle_btn.setToolTip("Ẩn key")
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("●●●")
            self.toggle_btn.setToolTip("Hiện key")

    def text(self) -> str:
        return self.input.text()

    def setText(self, text: str) -> None:
        self.input.setText(text)

    def setPlaceholderText(self, placeholder: str) -> None:
        self.input.setPlaceholderText(placeholder)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.input.setEnabled(enabled)
        self.toggle_btn.setEnabled(enabled)


def credential_field(placeholder: str = "") -> CredentialField:
    """Factory shorthand for CredentialField."""
    return CredentialField(placeholder)


# ─────────────────────────────────────────────────────────────────────────────
# STATUS BADGE
# ─────────────────────────────────────────────────────────────────────────────

def status_badge(text: str, state: str = "info") -> QLabel:
    """
    Compact status pill with icon prefix and semantic color.

    States: running | paused | success | warning | error | info | muted
    """
    tokens = get_tokens()

    _MAP = {
        "running":  (tokens["accent"],     tokens["info_bg"],      "●"),
        "paused":   (tokens["warn"],       tokens["warn_dim"],     "⏸"),
        "success":  (tokens["ok"],         tokens["ok_dim"],       "✓"),
        "warning":  (tokens["warn"],      tokens["warn_dim"],     "⚠"),
        "error":    (tokens["danger"],     tokens["danger_dim"],   "✗"),
        "info":     (tokens["info"],       tokens["info_bg"],      "◆"),
        "muted":    (tokens["text_low"],   tokens["bg_surface"],   "○"),
    }

    fg, bg, prefix = _MAP.get(state, _MAP["info"])
    lbl = QLabel(f"{prefix}  {text}")
    lbl.setStyleSheet(f"""
        QLabel {{
            color: {fg};
            background-color: {bg};
            border: 1px solid {fg};
            border-radius: 5px;
            padding: 2px 9px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.4px;
        }}
    """)
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# INFO / WARNING BANNER
# ─────────────────────────────────────────────────────────────────────────────

def info_banner(text: str, state: str = "info", icon: str = "") -> QFrame:
    """
    Horizontal contextual banner strip.

    state: "info" | "warning" | "error" | "success"
    """
    tokens = get_tokens()

    _BANNER = {
        "info":    (tokens["info"],    tokens["info_bg"],    tokens["border_accent"], "ℹ"),
        "warning": (tokens["warn"],    tokens["warn_dim"],   tokens["warn"],          "⚠"),
        "error":   (tokens["danger"],  tokens["danger_dim"], tokens["danger"],        "✗"),
        "success": (tokens["ok"],      tokens["ok_dim"],     tokens["ok"],            "✓"),
    }
    fg, bg, bdr, default_icon = _BANNER.get(state, _BANNER["info"])
    actual_icon = icon or default_icon

    obj_name = "warningBanner" if state == "warning" else "infoBanner"
    banner = QFrame()
    banner.setObjectName(obj_name)
    banner.setStyleSheet(f"""
        QFrame#{obj_name} {{
            background-color: {bg};
            border: 1px solid {bdr};
            border-radius: 8px;
        }}
    """)

    layout = QHBoxLayout(banner)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(10)

    ic = QLabel(actual_icon)
    ic.setStyleSheet(f"font-size: 13px; color: {fg}; background: transparent; font-weight: 700;")
    ic.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    layout.addWidget(ic)

    msg = QLabel(text)
    msg.setWordWrap(True)
    msg.setStyleSheet(
        f"font-size: 12px; color: {fg}; background: transparent; font-weight: 500;"
    )
    layout.addWidget(msg, stretch=1)

    return banner


# ─────────────────────────────────────────────────────────────────────────────
# STAT ROW WIDGET
# ─────────────────────────────────────────────────────────────────────────────

def stat_row_widget(
    success: int = 0,
    skipped: int = 0,
    failed: int = 0,
) -> Tuple[QWidget, "QLabel", "QLabel", "QLabel"]:
    """
    Compact 3-counter summary row (success / skipped / failed).

    Returns (container_widget, success_lbl, skipped_lbl, failed_lbl)
    so callers can update labels via setText().
    """
    tokens = get_tokens()
    wrap = QWidget()
    wrap.setStyleSheet("background: transparent;")
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(24)

    def _make_stat(icon: str, value: int, color: str) -> QLabel:
        lbl = QLabel(f"{icon}  {value}")
        lbl.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 700; "
            f"background: transparent; letter-spacing: 0.2px;"
        )
        return lbl

    s_lbl = _make_stat("✓", success, tokens["ok"])
    sk_lbl = _make_stat("⊘", skipped, tokens["text_low"])
    f_lbl = _make_stat("✗", failed, tokens["danger"])

    row.addWidget(s_lbl)
    row.addWidget(sk_lbl)
    row.addWidget(f_lbl)
    row.addStretch()

    return wrap, s_lbl, sk_lbl, f_lbl


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def section_spacer(height: int = 8) -> QWidget:
    """Thin vertical spacer."""
    w = QWidget()
    w.setFixedHeight(height)
    w.setStyleSheet("background: transparent;")
    return w


def divider() -> QFrame:
    """Thin horizontal rule for within-section separation."""
    line = QFrame()
    line.setObjectName("headerRule")
    line.setFrameShape(QFrame.Shape.HLine)
    return line


# ─────────────────────────────────────────────────────────────────────────────
# QUOTA RING — circular arc quota indicator
# ─────────────────────────────────────────────────────────────────────────────

class QuotaRing(QWidget):
    """Circular SVG-style quota ring with color-coded arc.

    Usage::

        ring = QuotaRing(size=52)
        ring.set_quota(0.72, "14.337")  # 72% remaining

    Colour thresholds (per File 4 §2.3):
        pct > 0.35  → ok    (#3fb950)
        pct > 0.12  → warn  (#d29922)
        else        → danger (#f85149)
    """

    def __init__(self, size: int = 52, parent=None):
        super().__init__(parent)
        self._size = size
        self._pct = 1.0
        self._label = ""
        self.setFixedSize(size, size)
        self.setStyleSheet("background: transparent;")

    def set_quota(self, pct: float, label: str = "") -> None:
        """Update the ring arc and label.

        Args:
            pct: 0.0–1.0 remaining quota fraction.
            label: Short text drawn inside the ring (e.g. "14.337").
        """
        self._pct = max(0.0, min(1.0, pct))
        self._label = label
        self.update()

    def _arc_color(self) -> str:
        tokens = get_tokens()
        if self._pct > 0.35:
            return tokens["ok"]
        elif self._pct > 0.12:
            return tokens["warn"]
        return tokens["danger"]

    def paintEvent(self, _event) -> None:
        tokens = get_tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._size
        margin = 5
        pen_w = 4
        r = (s - margin * 2 - pen_w) / 2.0
        cx, cy = s / 2.0, s / 2.0

        # Background track
        pen = QPen(QColor(tokens["bg_raised"]), pen_w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 0, 360 * 16)

        # Foreground arc
        arc_color = QColor(self._arc_color())
        pen2 = QPen(arc_color, pen_w)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        span = int(360 * 16 * self._pct)
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, -span)

        # Percentage text
        pct_str = f"{int(self._pct * 100)}%"
        font = QFont("JetBrains Mono", 10, 700)
        p.setFont(font)
        p.setPen(QColor(tokens["text_hi"]))
        p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, pct_str)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# STAT CARD
# ─────────────────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Dark elevated card with a large stat number, label, and optional trend.

    Usage::

        card = StatCard("14.337", "Hạn mức còn lại", trend="↑ 12%")
    """

    def __init__(self, value: str = "", label: str = "",
                 trend: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        tokens = get_tokens()

        self.setStyleSheet(
            f"QFrame#statCard {{ background-color: {tokens['bg_raised']}; "
            f"border: 1px solid {tokens['border']}; border-radius: 10px; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        self._val = QLabel(value)
        self._val.setProperty("statNumber", True)
        lay.addWidget(self._val)

        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(
            f"font-size: 11px; color: {tokens['text_low']}; "
            f"font-weight: 500; background: transparent;"
        )
        lay.addWidget(self._lbl)

        self._trend = QLabel(trend)
        if trend:
            self._trend.setStyleSheet(
                f"font-size: 10px; color: {tokens['ok']}; "
                f"font-weight: 600; background: transparent;"
            )
        else:
            self._trend.setVisible(False)
        lay.addWidget(self._trend)

    def set_value(self, value: str) -> None:
        self._val.setText(value)

    def set_label(self, label: str) -> None:
        self._lbl.setText(label)

    def set_trend(self, trend: str, up: bool = True) -> None:
        tokens = get_tokens()
        self._trend.setText(trend)
        self._trend.setVisible(bool(trend))
        if trend:
            self._trend.setStyleSheet(
                f"font-size: 10px; color: {tokens['ok'] if up else tokens['danger']}; "
                f"font-weight: 600; background: transparent;"
            )


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE PREVIEW CARD
# ─────────────────────────────────────────────────────────────────────────────

class ImagePreviewCard(QFrame):
    """Image result card with thumbnail, title, verification badge, and CLIP score.

    Matches the layout defined in File 4 §5.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        tokens = get_tokens()
        self.setObjectName("providerCard")
        self.setFixedWidth(220)
        self.setStyleSheet(
            f"QFrame#providerCard {{ background-color: {tokens['bg_surface']}; "
            f"border: 1px solid {tokens['border']}; border-radius: 14px; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedHeight(120)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet(
            f"background-color: {tokens['bg_raised']}; "
            f"border-radius: 8px; border: none;"
        )
        lay.addWidget(self.thumb)

        # Title
        self.title = QLabel("")
        self.title.setWordWrap(True)
        self.title.setMaximumHeight(32)
        self.title.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {tokens['text_hi']}; "
            f"background: transparent;"
        )
        lay.addWidget(self.title)

        # Badge row
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(6)
        self.badge = QLabel("")
        self.badge.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {tokens['accent']}; "
            f"background: {tokens['accent_dim']}; border-radius: 4px; "
            f"padding: 1px 6px;"
        )
        self.badge.setVisible(False)
        badge_row.addWidget(self.badge)
        badge_row.addStretch()
        lay.addLayout(badge_row)

        # CLIP score
        self.clip = QLabel("")
        self.clip.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace; "
            f"font-size: 11px; color: {tokens['text_low']}; "
            f"background: transparent; font-weight: 500;"
        )
        self.clip.setVisible(False)
        lay.addWidget(self.clip)

        # Attribution
        self.attr = QLabel("")
        self.attr.setWordWrap(True)
        self.attr.setStyleSheet(
            f"font-size: 10px; color: {tokens['text_low']}; "
            f"background: transparent;"
        )
        self.attr.setVisible(False)
        lay.addWidget(self.attr)

        lay.addStretch()

    def set_image(self, pixmap) -> None:
        """Set the thumbnail pixmap, scaled to fit."""
        scaled = pixmap.scaled(
            200, 120,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.thumb.setPixmap(scaled)

    def set_placeholder(self) -> None:
        """Show a placeholder when no image is loaded."""
        tokens = get_tokens()
        self.thumb.setText("🖼")
        self.thumb.setStyleSheet(
            f"font-size: 32px; color: {tokens['text_disabled']}; "
            f"background-color: {tokens['bg_raised']}; "
            f"border-radius: 8px; border: none;"
        )
