"""Reusable UI building blocks for AnkiAI settings dialogs."""

from aqt.qt import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)


def make_settings_card() -> tuple:
    """Return (card frame, inner layout)."""
    card = QFrame()
    card.setObjectName("settingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(8)
    return card, layout


def card_header(icon: str, title: str) -> QLabel:
    label = QLabel(f"{icon}  {title}")
    label.setProperty("cardTitle", True)
    return label


def field_row(label: str, hint: str = "", badge: str = "") -> QWidget:
    """Label row with optional hint and badge (priority | recommended)."""
    wrap = QWidget()
    row = QVBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(2)

    top = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setProperty("fieldLabel", True)
    top.addWidget(lbl)
    if badge == "priority":
        b = QLabel("Ưu tiên")
        b.setProperty("badge", "priority")
        top.addWidget(b)
    elif badge == "recommended":
        b = QLabel("Khuyến nghị")
        b.setProperty("badge", "recommended")
        top.addWidget(b)
    top.addStretch()
    row.addLayout(top)

    if hint:
        h = QLabel(hint)
        h.setProperty("hint", True)
        h.setWordWrap(True)
        row.addWidget(h)
    return wrap


def password_field(placeholder: str = "") -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    if placeholder:
        field.setPlaceholderText(placeholder)
    return field


def section_spacer() -> QWidget:
    w = QWidget()
    w.setFixedHeight(10)
    return w
