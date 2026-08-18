"""AnkiAI Theme Engine — Premium Futuristic AI Desktop Design System.

Visual language extracted from high-end digital-agency cinematic aesthetic:
  - Deep midnight navy / near-black foundation
  - Electric Blue (#00A3FF) primary accent
  - Violet (#8A2BE2) secondary accent
  - Layered depth surfaces (4 elevation levels)
  - Restrained glow on primary interactive elements
  - Blue-to-violet gradient on CTA buttons
  - Sophisticated typography hierarchy
  - Clean, muted, high-contrast text system

Safe string-template interpolation (template % t) — no f-string dict keys.
Compatible with Python 3.9–3.13.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1. SEMANTIC COLOR TOKENS
# ============================================================================

THEME_TOKENS_DARK: Dict[str, str] = {
    # ── Backgrounds — 4-layer depth hierarchy ───────────────────────────────
    "bg_window":      "#080A10",   # Deepest canvas (midnight black-navy)
    "bg_surface":     "#0D1018",   # Primary card surface
    "bg_elevated":    "#111520",   # Elevated panel, hover state
    "bg_elevated2":   "#161B28",   # Active / focused surface
    "bg_input":       "#090C13",   # Input field well

    # ── Borders ─────────────────────────────────────────────────────────────
    "border":         "#1A2035",   # Default structural border
    "border_light":   "#222B42",   # Slightly lighter separator
    "border_focus":   "#00A3FF",   # Focus — electric blue
    "border_accent":  "#0070C0",   # Accent border (subtle panels)
    "border_violet":  "#5B21B6",   # Violet accent border

    # ── Primary Accent — Electric Blue ──────────────────────────────────────
    "accent":         "#00A3FF",   # Electric blue
    "accent_hover":   "#33B8FF",   # Brighter on hover
    "accent_pressed": "#0082CC",   # Pressed / active
    "accent_dim":     "#0070C0",   # Dimmed background tints
    "accent_glow":    "#00A3FF40", # Glow color (40 = 25% opacity)

    # ── Secondary Accent — Violet ────────────────────────────────────────────
    "accent_violet":       "#8A2BE2",
    "accent_violet_hover": "#9D50E0",
    "accent_violet_dim":   "#4C1D95",
    "accent_violet_glow":  "#8A2BE230",

    # ── Gradient stops for primary buttons ──────────────────────────────────
    "grad_start":     "#0082CC",   # Left side — deep blue
    "grad_end":       "#6D28D9",   # Right side — violet

    # ── Teal secondary (AI features) ────────────────────────────────────────
    "accent_teal":    "#14B8A6",
    "accent_teal_dim":"#0F766E",

    # ── Text ────────────────────────────────────────────────────────────────
    "text_primary":   "#F5F7FA",   # Soft white — headings
    "text_secondary": "#B0B7C3",   # Cool light gray — labels
    "text_muted":     "#7E8796",   # Desaturated blue-gray — hints
    "text_disabled":  "#3A4255",   # Disabled state

    # ── Semantic States ──────────────────────────────────────────────────────
    "success":        "#10B981",
    "success_bg":     "#021A12",
    "warning":        "#F59E0B",
    "warning_bg":     "#1A0F00",
    "danger":         "#EF4444",
    "danger_bg":      "#1C0505",
    "danger_hover":   "#DC2626",
    "info":           "#38BDF8",
    "info_bg":        "#030F1C",

    # ── Tab Components ───────────────────────────────────────────────────────
    "tab_active_bg":  "#0D1018",
    "tab_inactive_bg":"#080A10",

    # ── Scrollbar ────────────────────────────────────────────────────────────
    "scrollbar_thumb":"#1A2035",
    "scrollbar_hover":"#222B42",
}

THEME_TOKENS_LIGHT: Dict[str, str] = {
    # ── Backgrounds ──────────────────────────────────────────────────────────
    "bg_window":      "#EEF2F7",
    "bg_surface":     "#FFFFFF",
    "bg_elevated":    "#F5F8FC",
    "bg_elevated2":   "#E8EFF8",
    "bg_input":       "#FFFFFF",

    # ── Borders ──────────────────────────────────────────────────────────────
    "border":         "#D8E2EF",
    "border_light":   "#C4D2E4",
    "border_focus":   "#0070C0",
    "border_accent":  "#0070C0",
    "border_violet":  "#7C3AED",

    # ── Primary Accent — Deep Blue ───────────────────────────────────────────
    "accent":         "#0070C0",
    "accent_hover":   "#0082CC",
    "accent_pressed": "#005999",
    "accent_dim":     "#005999",
    "accent_glow":    "#0070C020",

    # ── Secondary Accent — Violet ────────────────────────────────────────────
    "accent_violet":       "#7C3AED",
    "accent_violet_hover": "#6D28D9",
    "accent_violet_dim":   "#4C1D95",
    "accent_violet_glow":  "#7C3AED20",

    # ── Gradient ─────────────────────────────────────────────────────────────
    "grad_start":     "#0070C0",
    "grad_end":       "#5B21B6",

    # ── Teal ─────────────────────────────────────────────────────────────────
    "accent_teal":    "#0D9488",
    "accent_teal_dim":"#0F766E",

    # ── Text ─────────────────────────────────────────────────────────────────
    "text_primary":   "#0D1117",
    "text_secondary": "#344054",
    "text_muted":     "#667085",
    "text_disabled":  "#98A2B3",

    # ── Semantic States ───────────────────────────────────────────────────────
    "success":        "#059669",
    "success_bg":     "#ECFDF5",
    "warning":        "#D97706",
    "warning_bg":     "#FFFBEB",
    "danger":         "#DC2626",
    "danger_bg":      "#FEF2F2",
    "danger_hover":   "#B91C1C",
    "info":           "#0284C7",
    "info_bg":        "#F0F9FF",

    # ── Tabs ──────────────────────────────────────────────────────────────────
    "tab_active_bg":  "#FFFFFF",
    "tab_inactive_bg":"#EEF2F7",

    # ── Scrollbar ─────────────────────────────────────────────────────────────
    "scrollbar_thumb":"#C4D2E4",
    "scrollbar_hover":"#98A2B3",
}

# Backward-compat constants (dark palette defaults)
BG_WINDOW    = THEME_TOKENS_DARK["bg_window"]
BG_CARD      = THEME_TOKENS_DARK["bg_surface"]
BG_INPUT     = THEME_TOKENS_DARK["bg_input"]
BORDER       = THEME_TOKENS_DARK["border"]
TEXT_PRIMARY = THEME_TOKENS_DARK["text_primary"]
TEXT_MUTED   = THEME_TOKENS_DARK["text_muted"]
ACCENT       = THEME_TOKENS_DARK["accent"]
ACCENT_DIM   = THEME_TOKENS_DARK["accent_dim"]
ACCENT_GOLD  = THEME_TOKENS_DARK["warning"]


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
    """
    t = THEME_TOKENS_DARK if dark else THEME_TOKENS_LIGHT

    # Pieces that need separate interpolation (avoid %% complexity)
    btn_primary_gradient = (
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        " stop:0 %(grad_start)s, stop:1 %(grad_end)s);"
    ) % t

    btn_primary_gradient_hover = (
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        " stop:0 %(accent_hover)s, stop:1 %(accent_violet_hover)s);"
    ) % t

    progress_gradient = (
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        " stop:0 %(accent_dim)s, stop:0.6 %(accent)s, stop:1 %(accent_violet)s);"
    ) % t

    template = ("""
    /* =========================================================
       BASE
       ========================================================= */
    QDialog {
        background-color: %(bg_window)s;
        color: %(text_primary)s;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }

    QWidget {
        color: %(text_primary)s;
        font-size: 13px;
    }

    /* =========================================================
       TYPOGRAPHY HIERARCHY
       ========================================================= */

    /* Dialog title */
    QLabel[heading="true"] {
        font-size: 18px;
        font-weight: 700;
        color: %(text_primary)s;
        letter-spacing: -0.4px;
        background: transparent;
    }

    /* Dialog subtitle */
    QLabel[subheading="true"] {
        font-size: 12px;
        font-weight: 400;
        color: %(text_muted)s;
        background: transparent;
    }

    /* Card / section title */
    QLabel[cardTitle="true"] {
        font-size: 10px;
        font-weight: 700;
        color: %(accent)s;
        letter-spacing: 1.2px;
        background: transparent;
    }

    /* Form field label */
    QLabel[fieldLabel="true"] {
        font-size: 12px;
        font-weight: 600;
        color: %(text_secondary)s;
        background: transparent;
    }

    /* Helper / hint */
    QLabel[hint="true"] {
        font-size: 11px;
        font-weight: 400;
        color: %(text_muted)s;
        line-height: 1.4;
        background: transparent;
    }

    /* Muted metadata */
    QLabel[muted="true"] {
        font-size: 12px;
        color: %(text_muted)s;
        background: transparent;
    }

    /* Generic fallback */
    QLabel {
        color: %(text_primary)s;
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
        background-color: %(warning_bg)s;
        color: %(warning)s;
        border: 1px solid %(warning)s;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 10px;
        font-weight: 600;
    }

    QLabel[badge="optional"] {
        background-color: transparent;
        color: %(text_muted)s;
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
        background-color: %(bg_elevated)s;
        border: 1px solid %(border)s;
        border-radius: 10px;
    }

    QFrame#infoBanner {
        background-color: %(info_bg)s;
        border: 1px solid %(border_accent)s;
        border-radius: 8px;
    }

    QFrame#warningBanner {
        background-color: %(warning_bg)s;
        border: 1px solid %(warning)s;
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
        color: %(text_muted)s;
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
        background-color: %(bg_elevated)s;
        color: %(text_secondary)s;
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
        background-color: %(bg_input)s;
        color: %(text_primary)s;
        border: 1px solid %(border_light)s;
        border-radius: 8px;
        padding: 8px 12px;
        min-height: 22px;
        selection-background-color: %(accent_dim)s;
        selection-color: %(text_primary)s;
        font-size: 12px;
    }

    QLineEdit:hover, QSpinBox:hover {
        border-color: %(border_accent)s;
    }

    QLineEdit:focus, QSpinBox:focus {
        border: 1px solid %(border_focus)s;
        background-color: %(bg_elevated)s;
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
        background-color: %(bg_input)s;
        color: %(text_primary)s;
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
        background-color: %(bg_elevated)s;
        color: %(text_primary)s;
        border: 1px solid %(border_light)s;
        border-radius: 6px;
        selection-background-color: %(accent_dim)s;
        selection-color: %(text_primary)s;
        padding: 4px;
        outline: none;
    }

    /* =========================================================
       BUTTONS — HIERARCHY
       ========================================================= */

    /* Base / tertiary */
    QPushButton {
        background-color: %(bg_elevated)s;
        color: %(text_secondary)s;
        border: 1px solid %(border_light)s;
        border-radius: 8px;
        padding: 9px 20px;
        font-size: 12px;
        font-weight: 600;
        min-height: 20px;
        letter-spacing: 0.3px;
    }

    QPushButton:hover {
        background-color: %(bg_elevated2)s;
        border-color: %(border_accent)s;
        color: %(text_primary)s;
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

    /* Secondary / ghost */
    QPushButton[secondary="true"] {
        background-color: transparent;
        color: %(text_muted)s;
        border: 1px solid %(border)s;
    }

    QPushButton[secondary="true"]:hover {
        background-color: %(bg_elevated)s;
        color: %(text_secondary)s;
        border-color: %(border_light)s;
    }

    /* Danger */
    QPushButton[danger="true"] {
        background-color: %(danger_bg)s;
        color: %(danger)s;
        border: 1px solid %(danger)s;
        border-radius: 8px;
    }

    QPushButton[danger="true"]:hover {
        background-color: %(danger)s;
        color: #FFFFFF;
    }

    QPushButton[danger="true"]:pressed {
        background-color: %(danger_hover)s;
    }

    /* Tool button */
    QToolButton {
        background-color: %(bg_elevated)s;
        color: %(text_muted)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 5px 8px;
        font-size: 11px;
    }

    QToolButton:hover {
        background-color: %(bg_elevated2)s;
        color: %(text_primary)s;
        border-color: %(border_light)s;
    }

    /* =========================================================
       CHECKBOX
       ========================================================= */
    QCheckBox {
        spacing: 9px;
        color: %(text_secondary)s;
        font-size: 12px;
        font-weight: 500;
    }

    QCheckBox:hover {
        color: %(text_primary)s;
    }

    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-radius: 4px;
        background-color: %(bg_input)s;
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
        background-color: %(bg_input)s;
        text-align: center;
        color: %(text_primary)s;
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
        background-color: %(bg_input)s;
        color: %(text_primary)s;
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
        background-color: %(bg_elevated2)s;
        color: %(text_primary)s;
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
        color: %(text_primary)s;
    }

    QMessageBox QLabel {
        color: %(text_primary)s;
        font-size: 13px;
    }
    """)

    css = template % t

    # Append gradient rules that need separate interpolation
    css += """
    QPushButton[primary="true"] {
        """ + btn_primary_gradient + """
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }
    QPushButton[primary="true"]:hover {
        """ + btn_primary_gradient_hover + """
        border: none;
    }
    QPushButton[primary="true"]:pressed {
        background-color: """ + t["accent_pressed"] + """;
        border: none;
    }
    QPushButton[primary="true"]:disabled {
        background-color: """ + t["bg_elevated"] + """;
        color: """ + t["text_disabled"] + """;
        border: none;
    }
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
