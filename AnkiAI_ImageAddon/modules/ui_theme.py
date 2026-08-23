"""AnkiAI Theme Engine — Cinematic Dark · Electric Cyan Design System.

Visual language (per File 1 §2 + UI_INDEX final design choice):
  - Deep midnight foundation (#0a0e14)
  - Electric Cyan (#00b4d8) single accent — NO violet
  - 4-layer elevation by background shade (no box-shadow)
  - CTA buttons: gradient #0077ff → #00e5ff (Cinematic Electric Cyan)
  - Alpha via rgba(), never hex 8-digit (Qt QSS errata E1)
  - Skeleton shimmer: cyan rgba(0,229,255,0.10) (matching accent identity)

Safe string-template interpolation (template % t) — no f-string dict keys.
Compatible with Python 3.9–3.13.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1. SEMANTIC COLOR TOKENS
# ============================================================================

THEME_TOKENS_DARK: Dict[str, str] = {
    # ── Backgrounds — 4-layer depth hierarchy ───────────────────────────────
    "bg_window":      "#0a0e14",   # Deepest canvas (L0)
    "bg_surface":     "#10151d",   # Card / panel level 1 (L1)
    "bg_raised":      "#161c26",   # Hover, input (L2)
    "bg_overlay":     "#1c2430",   # Dropdown, overlay, pressed (L3)

    # ── Borders ─────────────────────────────────────────────────────────────
    "border":         "#232c3b",   # Default structural border
    "border_light":   "#2c3646",   # Hover border, separator
    "border_focus":   "#00b4d8",   # Focus ring
    "border_accent":  "#155e75",   # Accent panel border

    # ── Primary Accent — Electric Cyan (SINGLE accent, no violet) ───────────
    "accent":         "#00b4d8",   # Main accent
    "accent_bright":  "#00e5ff",   # Highlight, brand, hover accent
    "accent_hover":   "#33c6ff",   # Hover CTA
    "accent_pressed": "#0090e8",   # Pressed CTA
    "accent_dim":     "#0a3d4d",   # Dimmed background tints
    "accent_glow":    "rgba(0,180,216,0.25)",  # Glow (rgba ONLY, never hex 8-digit)

    # ── Gradient stops (progress bar, brand text — NOT for CTA buttons) ────
    "grad_start":     "#0077ff",
    "grad_end":       "#00e5ff",

    # ── AI feature accent (Imagen only) ─────────────────────────────────────
    "accent_ai":      "#14b8a6",

    # ── Text ────────────────────────────────────────────────────────────────
    "text_hi":        "#e6edf3",   # Headings, primary text
    "text_mid":       "#c9d1d9",   # Labels, secondary text
    "text_low":       "#8b949e",   # Captions ≥12px
    "text_disabled":  "#4b5563",   # Disabled state
    "text_inv":       "#04121a",   # Text on accent background

    # ── Semantic States ─────────────────────────────────────────────────────
    "ok":             "#3fb950",
    "ok_dim":         "#10321a",
    "warn":           "#d29922",
    "warn_dim":       "#3a2a08",
    "danger":         "#f85149",
    "danger_dim":     "#3d1214",
    "info":           "#58a6ff",
    "info_bg":        "#0c2d4d",

    # ── Tabs ────────────────────────────────────────────────────────────────
    "tab_active_bg":  "#10151d",
    "tab_inactive_bg":"#0a0e14",

    # ── Scrollbar ───────────────────────────────────────────────────────────
    "scrollbar_thumb":"#232c3b",
    "scrollbar_hover":"#2c3646",

    # ── Skeleton shimmer (NEUTRAL — anti-AI-slop, not cyan) ─────────────────
    "shimmer_band":   "rgba(255,255,255,0.06)",
}

THEME_TOKENS_LIGHT: Dict[str, str] = {
    # ── Backgrounds ─────────────────────────────────────────────────────────
    "bg_window":      "#eef2f7",
    "bg_surface":     "#ffffff",
    "bg_raised":      "#f5f8fc",
    "bg_overlay":     "#e8eff8",

    # ── Borders ─────────────────────────────────────────────────────────────
    "border":         "#d8e2ef",
    "border_light":   "#c4d2e4",
    "border_focus":   "#0070c0",
    "border_accent":  "#0070c0",

    # ── Primary Accent — Deep Blue ──────────────────────────────────────────
    "accent":         "#0070c0",
    "accent_bright":  "#00a3ff",
    "accent_hover":   "#0082cc",
    "accent_pressed": "#005999",
    "accent_dim":     "#005999",
    "accent_glow":    "rgba(0,112,192,0.15)",

    # ── Gradient ────────────────────────────────────────────────────────────
    "grad_start":     "#0070c0",
    "grad_end":       "#00a3ff",

    # ── AI feature accent ───────────────────────────────────────────────────
    "accent_ai":      "#0d9488",

    # ── Text ────────────────────────────────────────────────────────────────
    "text_hi":        "#0d1117",
    "text_mid":       "#344054",
    "text_low":       "#667085",
    "text_disabled":  "#98a2b3",
    "text_inv":       "#ffffff",

    # ── Semantic States ─────────────────────────────────────────────────────
    "ok":             "#059669",
    "ok_dim":         "#ecfdf5",
    "warn":           "#d97706",
    "warn_dim":       "#fffbeb",
    "danger":         "#dc2626",
    "danger_dim":     "#fef2f2",
    "info":           "#0284c7",
    "info_bg":        "#f0f9ff",

    # ── Tabs ────────────────────────────────────────────────────────────────
    "tab_active_bg":  "#ffffff",
    "tab_inactive_bg":"#eef2f7",

    # ── Scrollbar ───────────────────────────────────────────────────────────
    "scrollbar_thumb":"#c4d2e4",
    "scrollbar_hover":"#98a2b3",

    # ── Skeleton shimmer (neutral) ──────────────────────────────────────────
    "shimmer_band":   "rgba(0,0,0,0.04)",
}

# Backward-compat constants (dark palette defaults)
BG_WINDOW    = THEME_TOKENS_DARK["bg_window"]
BG_CARD      = THEME_TOKENS_DARK["bg_surface"]
BG_INPUT     = THEME_TOKENS_DARK["bg_raised"]
BORDER       = THEME_TOKENS_DARK["border"]
TEXT_PRIMARY = THEME_TOKENS_DARK["text_hi"]
TEXT_MUTED   = THEME_TOKENS_DARK["text_low"]
ACCENT       = THEME_TOKENS_DARK["accent"]
ACCENT_DIM   = THEME_TOKENS_DARK["accent_dim"]
ACCENT_GOLD  = THEME_TOKENS_DARK["warn"]

# Font stacks (per INDEX §2.2)
FONT_UI = 'Inter, -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
FONT_MONO = '"JetBrains Mono", "SF Mono", Consolas, "Roboto Mono", monospace'


# ============================================================================
# 2. THEME DETECTION
# ============================================================================

def is_dark_mode(widget=None) -> bool:
    """Detect Anki Night Mode or OS palette luminance."""
    try:
        from aqt import mw
        if mw and hasattr(mw, "pm") and hasattr(mw.pm, "night_mode"):
            return bool(mw.pm.night_mode())
    except Exception:
        pass

    if widget is not None:
        try:
            palette = widget.palette()
            bg = palette.window().color()
            luminance = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
            return luminance < 128
        except Exception:
            pass

    return True  # Default dark — our primary design identity


def get_tokens(dark: Optional[bool] = None) -> Dict[str, str]:
    """Return semantic token dict for dark or light mode."""
    if dark is None:
        dark = is_dark_mode()
    return THEME_TOKENS_DARK if dark else THEME_TOKENS_LIGHT


# ============================================================================
# 3. CENTRALIZED QSS STYLESHEET GENERATOR
# ============================================================================

def build_stylesheet(dark: bool = True) -> str:
    """
    Generate the full desktop Qt stylesheet.
    Uses %(key)s % dict — safe on Python 3.9–3.13.

    Key design decisions (Cinematic Dark · Electric Cyan):
    - CTA buttons: gradient #0077ff → #00e5ff
    - Glow simulated via accent_dim borders (Qt QSS has no box-shadow)
    - Alpha via rgba(), never hex 8-digit
    """
    t = THEME_TOKENS_DARK if dark else THEME_TOKENS_LIGHT

    progress_gradient = (
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        " stop:0 %(grad_start)s, stop:1 %(grad_end)s);"
    ) % t

    cta_gradient = (
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        " stop:0 %(grad_start)s, stop:1 %(grad_end)s);"
    ) % t

    cta_gradient_hover = (
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        " stop:0 %(accent_hover)s, stop:1 %(grad_end)s);"
    ) % t

    # Merged dict so the template can reference gradient blocks by name
    tt = dict(t)
    tt["cta_gradient"] = cta_gradient
    tt["cta_gradient_hover"] = cta_gradient_hover

    template = ("""
    /* =========================================================
       BASE
       ========================================================= */
    QDialog {
        background-color: %(bg_window)s;
        color: %(text_hi)s;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }

    QWidget {
        color: %(text_hi)s;
        font-size: 13px;
    }

    /* =========================================================
       TYPOGRAPHY HIERARCHY
       ========================================================= */

    /* Dialog title */
    QLabel[heading="true"] {
        font-size: 20px;
        font-weight: 700;
        color: %(text_hi)s;
        letter-spacing: -0.3px;
        background: transparent;
    }

    /* Dialog subtitle */
    QLabel[subheading="true"] {
        font-size: 12px;
        font-weight: 400;
        color: %(text_low)s;
        background: transparent;
    }

    /* Card / section title — uppercase accent label */
    QLabel[cardTitle="true"] {
        font-size: 10px;
        font-weight: 700;
        color: %(accent)s;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        background: transparent;
    }

    /* Form field label */
    QLabel[fieldLabel="true"] {
        font-size: 12px;
        font-weight: 600;
        color: %(text_mid)s;
        background: transparent;
    }

    /* Helper / hint */
    QLabel[hint="true"] {
        font-size: 11px;
        font-weight: 400;
        color: %(text_low)s;
        line-height: 1.4;
        background: transparent;
    }

    /* Muted metadata */
    QLabel[muted="true"] {
        font-size: 12px;
        color: %(text_low)s;
        background: transparent;
    }

    /* Stat / brand number — mono font */
    QLabel[statNumber="true"] {
        font-family: "JetBrains Mono", "SF Mono", Consolas, monospace;
        font-size: 24px;
        font-weight: 800;
        color: %(accent_bright)s;
        background: transparent;
        letter-spacing: -1px;
    }

    /* Generic fallback */
    QLabel {
        color: %(text_hi)s;
        background: transparent;
    }

    /* =========================================================
       BADGES
       ========================================================= */
    QLabel[badge="priority"] {
        background-color: %(accent_dim)s;
        color: %(accent)s;
        border: 1px solid %(accent_dim)s;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.6px;
    }

    QLabel[badge="recommended"] {
        background-color: %(warn_dim)s;
        color: %(warn)s;
        border: 1px solid %(warn)s;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 10px;
        font-weight: 600;
    }

    QLabel[badge="optional"] {
        background-color: transparent;
        color: %(text_low)s;
        border: 1px solid %(border_light)s;
        border-radius: 4px;
        padding: 1px 7px;
        font-size: 10px;
        font-weight: 500;
    }

    /* =========================================================
       SEPARATOR RULE
       ========================================================= */
    QFrame#headerRule {
        background-color: %(border)s;
        max-height: 1px;
        min-height: 1px;
        border: none;
    }

    /* =========================================================
       SECTION CONTAINERS / CARDS
       ========================================================= */
    QFrame#settingsSection {
        background-color: %(bg_surface)s;
        border: 1px solid %(border)s;
        border-radius: 12px;
    }

    QFrame#settingsCard {
        background-color: %(bg_surface)s;
        border: 1px solid %(border)s;
        border-radius: 12px;
    }

    QFrame#providerCard {
        background-color: %(bg_surface)s;
        border: 1px solid %(border)s;
        border-radius: 12px;
    }

    QFrame#providerCard:hover {
        border-color: %(border_accent)s;
    }

    QFrame#accentPanel {
        background-color: %(bg_surface)s;
        border: 1px solid %(border_accent)s;
        border-radius: 12px;
    }

    QFrame#statCard {
        background-color: %(bg_raised)s;
        border: 1px solid %(border)s;
        border-radius: 10px;
    }

    QFrame#infoBanner {
        background-color: %(info_bg)s;
        border: 1px solid %(border_accent)s;
        border-radius: 8px;
    }

    QFrame#warningBanner {
        background-color: %(warn_dim)s;
        border: 1px solid %(warn)s;
        border-radius: 8px;
    }

    /* =========================================================
       TAB WIDGET
       ========================================================= */
    QTabWidget::pane {
        border: 1px solid %(border)s;
        border-radius: 12px;
        background-color: %(bg_surface)s;
        top: -1px;
    }

    QTabBar::tab {
        background-color: %(tab_inactive_bg)s;
        color: %(text_low)s;
        border: 1px solid %(border)s;
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 9px 20px;
        margin-right: 3px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }

    QTabBar::tab:hover {
        background-color: %(bg_raised)s;
        color: %(text_mid)s;
    }

    QTabBar::tab:selected {
        background-color: %(tab_active_bg)s;
        color: %(accent)s;
        border-color: %(border_light)s;
        border-bottom: 2px solid %(accent)s;
    }

    /* =========================================================
       INPUTS
       ========================================================= */
    QLineEdit, QSpinBox {
        background-color: %(bg_raised)s;
        color: %(text_hi)s;
        border: 1px solid %(border_light)s;
        border-radius: 8px;
        padding: 8px 12px;
        min-height: 22px;
        selection-background-color: %(accent_dim)s;
        selection-color: %(text_hi)s;
        font-size: 12px;
    }

    QLineEdit:hover, QSpinBox:hover {
        border-color: %(border_accent)s;
    }

    QLineEdit:focus, QSpinBox:focus {
        border: 1px solid %(border_focus)s;
        background-color: %(bg_overlay)s;
    }

    QLineEdit::placeholder {
        color: %(text_disabled)s;
    }

    QLineEdit:disabled, QSpinBox:disabled {
        background-color: %(bg_surface)s;
        color: %(text_disabled)s;
        border-color: %(border)s;
    }

    QComboBox {
        background-color: %(bg_raised)s;
        color: %(text_hi)s;
        border: 1px solid %(border_light)s;
        border-radius: 8px;
        padding: 8px 12px;
        min-height: 22px;
        font-size: 12px;
    }

    QComboBox:hover {
        border-color: %(border_accent)s;
    }

    QComboBox:focus {
        border: 1px solid %(border_focus)s;
    }

    QComboBox::drop-down {
        border: none;
        width: 28px;
        padding-right: 8px;
    }

    QComboBox QAbstractItemView {
        background-color: %(bg_overlay)s;
        color: %(text_hi)s;
        border: 1px solid %(border_light)s;
        border-radius: 6px;
        selection-background-color: %(accent_dim)s;
        selection-color: %(text_hi)s;
        padding: 4px;
        outline: none;
    }

    /* =========================================================
       BUTTONS — HIERARCHY
       ========================================================= */

    /* Base / tertiary */
    QPushButton {
        background-color: %(bg_raised)s;
        color: %(text_mid)s;
        border: 1px solid %(border_light)s;
        border-radius: 8px;
        padding: 9px 20px;
        font-size: 12px;
        font-weight: 600;
        min-height: 20px;
        letter-spacing: 0.3px;
    }

    QPushButton:hover {
        background-color: %(bg_overlay)s;
        border-color: %(border_accent)s;
        color: %(text_hi)s;
    }

    QPushButton:pressed {
        background-color: %(bg_surface)s;
        border-color: %(accent)s;
    }

    QPushButton:disabled {
        background-color: %(bg_window)s;
        color: %(text_disabled)s;
        border-color: %(border)s;
    }

    /* PRIMARY CTA — gradient #0077ff→#00e5ff (Cinematic Electric Cyan) */
    QPushButton[primary="true"] {
        %(cta_gradient)s
        color: %(text_inv)s;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }

    QPushButton[primary="true"]:hover {
        %(cta_gradient_hover)s
        border: none;
    }

    QPushButton[primary="true"]:pressed {
        background-color: %(accent_pressed)s;
        border: none;
    }

    QPushButton[primary="true"]:disabled {
        background-color: %(bg_raised)s;
        color: %(text_disabled)s;
        border: none;
    }

    /* Secondary / ghost */
    QPushButton[secondary="true"] {
        background-color: transparent;
        color: %(text_low)s;
        border: 1px solid %(border)s;
    }

    QPushButton[secondary="true"]:hover {
        background-color: %(bg_raised)s;
        color: %(text_mid)s;
        border-color: %(border_light)s;
    }

    /* Danger */
    QPushButton[danger="true"] {
        background-color: %(danger_dim)s;
        color: %(danger)s;
        border: 1px solid %(danger)s;
        border-radius: 8px;
    }

    QPushButton[danger="true"]:hover {
        background-color: %(danger)s;
        color: %(text_inv)s;
    }

    QPushButton[danger="true"]:pressed {
        background-color: %(danger)s;
    }

    /* Tool button */
    QToolButton {
        background-color: %(bg_raised)s;
        color: %(text_low)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 5px 8px;
        font-size: 11px;
    }

    QToolButton:hover {
        background-color: %(bg_overlay)s;
        color: %(text_hi)s;
        border-color: %(border_light)s;
    }

    /* =========================================================
       CHECKBOX
       ========================================================= */
    QCheckBox {
        spacing: 9px;
        color: %(text_mid)s;
        font-size: 12px;
        font-weight: 500;
    }

    QCheckBox:hover {
        color: %(text_hi)s;
    }

    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-radius: 4px;
        background-color: %(bg_raised)s;
        border: 1px solid %(border_light)s;
    }

    QCheckBox::indicator:hover {
        border-color: %(accent_dim)s;
    }

    QCheckBox::indicator:checked {
        background-color: %(accent)s;
        border-color: %(accent)s;
    }

    QCheckBox::indicator:disabled {
        background-color: %(bg_surface)s;
        border-color: %(border)s;
    }

    /* =========================================================
       PROGRESS BAR
       ========================================================= */
    QProgressBar {
        border: 1px solid %(border)s;
        border-radius: 6px;
        background-color: %(bg_raised)s;
        text-align: center;
        color: %(text_hi)s;
        min-height: 14px;
        max-height: 14px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    QProgressBar::chunk {
        border-radius: 5px;
    }

    /* =========================================================
       SCROLL AREA & BARS
       ========================================================= */
    QScrollArea {
        border: none;
        background: transparent;
    }

    QScrollArea > QWidget > QWidget {
        background: transparent;
    }

    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 5px;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background: %(scrollbar_thumb)s;
        min-height: 30px;
        border-radius: 3px;
    }

    QScrollBar::handle:vertical:hover {
        background: %(scrollbar_hover)s;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        background: none;
    }

    QScrollBar:horizontal {
        border: none;
        background: transparent;
        height: 5px;
    }

    QScrollBar::handle:horizontal {
        background: %(scrollbar_thumb)s;
        min-width: 30px;
        border-radius: 3px;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
        background: none;
    }

    /* =========================================================
       TEXT BROWSER
       ========================================================= */
    QTextBrowser {
        background-color: %(bg_raised)s;
        color: %(text_hi)s;
        border: 1px solid %(border)s;
        border-radius: 8px;
        padding: 10px;
        font-size: 12px;
        selection-background-color: %(accent_dim)s;
    }

    /* =========================================================
       TOOLTIP
       ========================================================= */
    QToolTip {
        background-color: %(bg_overlay)s;
        color: %(text_hi)s;
        border: 1px solid %(border_light)s;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 11px;
    }

    /* =========================================================
       MESSAGE BOX
       ========================================================= */
    QMessageBox {
        background-color: %(bg_window)s;
        color: %(text_hi)s;
    }

    QMessageBox QLabel {
        color: %(text_hi)s;
        font-size: 13px;
    }
    """)

    css = template % tt

    # Append progress bar gradient (uses separate interpolation)
    css += """
    QProgressBar::chunk {
        """ + progress_gradient + """
        border-radius: 5px;
    }
    """
    return css


# Build default (dark) stylesheet at import time
DIALOG_STYLESHEET = build_stylesheet(dark=True)


def apply_dialog_theme(widget, dark: Optional[bool] = None) -> None:
    """Apply the centralized stylesheet to any dialog or widget."""
    if dark is None:
        dark = is_dark_mode(widget)
    widget.setStyleSheet(build_stylesheet(dark=dark))
