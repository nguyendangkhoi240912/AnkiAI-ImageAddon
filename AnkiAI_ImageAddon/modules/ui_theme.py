"""AnkiAI dark UI theme — Midnight Navy + Teal accent."""

# Palette
BG_WINDOW = "#161625"
BG_CARD = "#202035"
BG_INPUT = "#101018"
BORDER = "#3F3F3F"
TEXT_PRIMARY = "#F0F0F0"
TEXT_MUTED = "#A0A0A0"
ACCENT = "#14b8a6"  # Teal
ACCENT_DIM = "#0d9488"
ACCENT_GOLD = "#D4AF37"

DIALOG_STYLESHEET = f"""
QDialog {{
    background-color: {BG_WINDOW};
    color: {TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QLabel[heading="true"] {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    padding: 4px 0 8px 0;
}}

QLabel[cardTitle="true"] {{
    font-size: 14px;
    font-weight: 700;
    color: {ACCENT};
    padding: 4px 0 10px 0;
}}

QLabel[fieldLabel="true"] {{
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
    padding-top: 6px;
}}

QLabel[hint="true"] {{
    color: {TEXT_MUTED};
    font-size: 11px;
    padding: 0 0 4px 0;
}}

QLabel[badge="priority"] {{
    background-color: rgba(20, 184, 166, 0.2);
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
}}

QLabel[badge="recommended"] {{
    background-color: rgba(212, 175, 55, 0.15);
    color: {ACCENT_GOLD};
    border: 1px solid {ACCENT_GOLD};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
}}

QFrame#settingsCard {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QFrame#headerRule {{
    background-color: {BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 22px;
    selection-background-color: {ACCENT_DIM};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit::placeholder {{
    color: #6b7280;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
}}

QPushButton {{
    background-color: #2a2a42;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #32324f;
    border-color: {ACCENT};
}}

QPushButton[primary="true"] {{
    background-color: {ACCENT_DIM};
    color: #ffffff;
    border: none;
}}

QPushButton[primary="true"]:hover {{
    background-color: {ACCENT};
}}

QPushButton[danger="true"] {{
    background-color: #3b1f1f;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
}}

QCheckBox {{
    spacing: 10px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 44px;
    height: 24px;
    border-radius: 12px;
    background-color: #3F3F3F;
    border: 1px solid {BORDER};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QCheckBox::indicator:unchecked:hover {{
    background-color: #4a4a4a;
}}

QProgressBar {{
    border: none;
    border-radius: 8px;
    background: {BG_INPUT};
    text-align: center;
    color: {TEXT_PRIMARY};
    min-height: 22px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_DIM}, stop:1 {ACCENT});
    border-radius: 8px;
}}
"""


def apply_dialog_theme(widget) -> None:
    widget.setStyleSheet(DIALOG_STYLESHEET)
