"""Shared Qt styles for AnkiAI dialogs."""

DIALOG_STYLESHEET = """
QDialog {
    background-color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
QLabel {
    color: #1e293b;
}
QLabel[heading="true"] {
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
    margin-top: 8px;
}
QLabel[muted="true"] {
    color: #64748b;
    font-size: 12px;
}
QLineEdit, QComboBox, QSpinBox {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 20px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #3b82f6;
}
QPushButton {
    background-color: #e2e8f0;
    color: #0f172a;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #cbd5e1;
}
QPushButton[primary="true"] {
    background-color: #2563eb;
    color: #ffffff;
}
QPushButton[primary="true"]:hover {
    background-color: #1d4ed8;
}
QPushButton[danger="true"] {
    background-color: #fef2f2;
    color: #b91c1c;
}
QProgressBar {
    border: none;
    border-radius: 8px;
    background: #e2e8f0;
    text-align: center;
    min-height: 22px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #06b6d4);
    border-radius: 8px;
}
QCheckBox {
    spacing: 8px;
    color: #334155;
}
"""


def apply_dialog_theme(widget) -> None:
    widget.setStyleSheet(DIALOG_STYLESHEET)
